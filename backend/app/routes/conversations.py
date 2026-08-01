from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.conversation import Conversation, Message

router = APIRouter()


class ConversationOut(BaseModel):
    id: str
    title: str

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list | None

    class Config:
        from_attributes = True


@router.post("/conversations")
def create_conversation(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    conversation = Conversation(user_id=user_id)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {"id": conversation.id, "title": conversation.title}


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    conversations = db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.created_at.desc()).all()
    return [ConversationOut.model_validate(c) for c in conversations]


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()
    if not conversation:
        raise HTTPException(404, "Conversation not found")
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return [MessageOut.model_validate(m) for m in messages]