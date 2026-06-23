import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import httpx
from .database import get_db, User, Chat, Message
from .auth import current_user, admin_user

LM_API_URL = os.getenv("LM_API_URL", "http://127.0.0.1:1234/v1/chat/completions")
LM_MODEL = os.getenv("LM_MODEL", "google/gemma-4-e4b")
MAX_HISTORY_MESSAGES = 20

router = APIRouter(prefix="/api", tags=["chat"])


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class RenameChatRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=80)


async def send_to_lmstudio(messages: list[dict[str, str]], temperature: float = 0.7, max_tokens: int | None = None) -> dict:
    """Send chat history to LM Studio and return the raw JSON response."""
    payload = {
        "model": LM_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    timeout = httpx.Timeout(60.0, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(LM_API_URL, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="LM Studio did not respond in time")
    except httpx.ConnectError:
        raise HTTPException(status_code=502, detail="Cannot connect to LM Studio. Check that the local server is running.")
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"LM Studio returned an error: {exc.response.status_code}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LM Studio request failed: {exc}")


def _extract_assistant_reply(data: dict) -> str:
    """Read assistant text from an OpenAI-compatible API response."""
    try:
        reply = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise HTTPException(status_code=502, detail="Unexpected LM Studio response format")

    if not isinstance(reply, str) or not reply.strip():
        raise HTTPException(status_code=502, detail="LM Studio returned an empty response")
    return reply


def _chat_or_404(db: Session, chat_id: int, user_id: int) -> Chat:
    chat = db.query(Chat).filter_by(id=chat_id, user_id=user_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


async def generate_chat_title(user_message: str, assistant_reply: str) -> str | None:
    """Generate a short title for a new chat using the local model.

    This runs only for fresh chats so it stays easy to explain and does not affect every request.
    """
    prompt_messages = [
        {
            "role": "system",
            "content": (
                "Create a very short chat title based on the conversation. "
                "Use 2 to 6 words. Do not use quotes. Do not add punctuation at the end."
            ),
        },
        {
            "role": "user",
            "content": f"User message: {user_message}\\nAssistant reply: {assistant_reply}",
        },
    ]

    try:
        response = await send_to_lmstudio(prompt_messages, temperature=0.2, max_tokens=18)
        title = _extract_assistant_reply(response)
    except HTTPException:
        return None

    clean_title = " ".join(title.replace("\n", " ").split()).strip().strip('"').strip("'")
    if not clean_title:
        return None
    return clean_title[:80]


@router.post("/create_chat")
def create_chat(db: Session = Depends(get_db), user: User = Depends(current_user)):
    chat = Chat(user_id=user.id, title="New chat")
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return {"chat_id": chat.id, "title": chat.title, "message": "Chat created successfully"}


@router.get("/chats")
def list_chats(db: Session = Depends(get_db), user: User = Depends(current_user)):
    chats = db.query(Chat).filter_by(user_id=user.id).order_by(Chat.updated_at.desc()).all()
    return [
        {
            "id": chat.id,
            "title": chat.title,
            "created_at": chat.created_at.isoformat(),
            "updated_at": chat.updated_at.isoformat(),
        }
        for chat in chats
    ]


@router.patch("/chats/{chat_id}/title")
def rename_chat(chat_id: int, payload: RenameChatRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    chat = _chat_or_404(db, chat_id, user.id)
    chat.title = payload.title.strip()
    chat.updated_at = datetime.utcnow()
    db.commit()
    return {"id": chat.id, "title": chat.title}


@router.get("/chats/{chat_id}/messages")
def get_messages(chat_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    chat = _chat_or_404(db, chat_id, user.id)
    messages = db.query(Message).filter_by(chat_id=chat.id).order_by(Message.id.asc()).all()
    return [
        {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]


@router.post("/chats/{chat_id}/send")
async def send_message(chat_id: int, payload: SendMessageRequest, db: Session = Depends(get_db), user: User = Depends(current_user)):
    chat = _chat_or_404(db, chat_id, user.id)
    text = payload.message.strip()

    user_msg = Message(chat_id=chat.id, role="user", content=text)
    db.add(user_msg)

    should_generate_title = (chat.title == "New chat")
    chat.updated_at = datetime.utcnow()
    db.commit()

    stored_messages = (
        db.query(Message)
        .filter_by(chat_id=chat.id)
        .order_by(Message.id.asc())
        .all()
    )
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in stored_messages[-MAX_HISTORY_MESSAGES:]
    ]

    lm_response = await send_to_lmstudio(history)
    reply = _extract_assistant_reply(lm_response)

    bot_msg = Message(chat_id=chat.id, role="assistant", content=reply)
    db.add(bot_msg)

    if should_generate_title:
        generated_title = await generate_chat_title(text, reply)
        chat.title = generated_title or text[:60]

    chat.updated_at = datetime.utcnow()
    db.commit()

    return {"user": text, "assistant": reply, "chat_title": chat.title}


@router.delete("/chats/{chat_id}", status_code=204)
def delete_chat(chat_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    chat = _chat_or_404(db, chat_id, user.id)
    db.delete(chat)
    db.commit()


@router.get("/admin/stats")
def admin_stats(_: User = Depends(admin_user), db: Session = Depends(get_db)):
    return {
        "users": db.query(User).count(),
        "chats": db.query(Chat).count(),
        "messages": db.query(Message).count(),
    }
