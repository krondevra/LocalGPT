from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import httpx
from .database import get_db, User, Chat, Message
from .auth import current_user

LM_API_URL = "http://127.0.0.1:1234/v1/chat/completions"  # LM Studio API URL

# Create a new router for chat-related endpoints
router = APIRouter(prefix="/api", tags=["Chat"])

# Function to send messages to LM Studio API
async def send_to_lmstudio(message: str):
    payload = {
        "messages": [{"role": "user", "content": message}],
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(LM_API_URL, json=payload)
        response.raise_for_status()
        return response.json()

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
@router.post("/select_chat/id")
async def select_chat(chat_id: int, message: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    # Get the selected chat
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == user.id).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found or not associated with the user")

    # Save the message in the chat
    new_message = Message(chat_id=chat.id, content=message)
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # Send the message to LM Studio and get a response
    lmstudio_response = await send_to_lmstudio(message)

    return {
        "chat_id": chat.id,
        "message": new_message.content,
        "response": lmstudio_response.get("choices")[0].get("message").get("content")
    }

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
