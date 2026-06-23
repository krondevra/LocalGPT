from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import httpx
import os
from .database import get_db, User, Chat, Message
from .auth import current_user

LM_API_URL = "http://127.0.0.1:1234/v1/chat/completions"  # LM Studio API URL
LM_MODEL   = os.getenv("LM_MODEL", "openai/gpt-oss-20b@mxfp4")

# Create a new router for chat-related endpoints
router = APIRouter(prefix="/api", tags=["Chat"])

# Function to send messages to LM Studio API
async def send_to_lmstudio(messages):
    payload = {
        "model": LM_MODEL,
        "messages": messages,
    }

    timeout = httpx.Timeout(60.0, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(LM_API_URL, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="LM Studio did not respond in time")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"LM Studio request failed: {exc}")

# Route to create a new chat
@router.post("/create_chat")
async def create_chat(db: Session = Depends(get_db), user: User = Depends(current_user)):
    # Create a new chat session for the user
    new_chat = Chat(user_id=user.id)
    db.add(new_chat)
    db.commit()
    db.refresh(new_chat)
    return {"chat_id": new_chat.id, "message": "Chat created successfully"}

# Route to select a chat, send a message, and get a response
@router.post("/chats/{chat_id}/send")
async def send_message(
    chat_id: int,
    message: str = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(current_user)
):
    chat = db.query(Chat).filter_by(id=chat_id, user_id=user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or not associated with the user")

    # save user message
    user_msg = Message(chat_id=chat.id, role="user", content=message)
    db.add(user_msg)
    db.commit()

    # build history
    history = [
        {"role": m.role, "content": m.content}
        for m in chat.messages
    ]

    # send to LM Studio
    lm_response = await send_to_lmstudio(history)
    reply = lm_response["choices"][0]["message"]["content"]

    # save assistant message
    bot_msg = Message(chat_id=chat.id, role="assistant", content=reply)
    db.add(bot_msg)
    db.commit()

    return {
        "user": message,
        "assistant": reply
    }

@router.get("/chats")
def list_chats(db: Session = Depends(get_db), user: User = Depends(current_user)):
    chats = db.query(Chat).filter_by(user_id=user.id).all()
    return [{"id": c.id} for c in chats]

@router.get("/chats/{chat_id}/messages")
def get_messages(chat_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    chat = db.query(Chat).filter_by(id=chat_id, user_id=user.id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or not associated with the user")

    return [
        {"role": m.role, "content": m.content}
        for m in chat.messages
    ]

# Route to delete a chat
@router.delete("/delete_chat/id", status_code=204)
async def delete_chat(chat_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    # Get the chat by ID
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or not associated with the user")

    # Delete the chat and related messages
    db.delete(chat)
    db.commit()

    return
