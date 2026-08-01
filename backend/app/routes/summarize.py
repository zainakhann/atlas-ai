from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document, Chunk
from app.models.conversation import Conversation, Message
from app.core.security import get_current_user_id
from app.services.summarizer import map_reduce_summarize, analyze_document

router = APIRouter()

ANALYZE_LABELS = {
    "key_points": "Key points for",
    "questions": "Questions answered by",
    "simplify": "Simple explanation of",
}


def _get_or_create_conversation(db: Session, conversation_id: str | None, user_id: str, default_title: str) -> Conversation:
    if conversation_id:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id, Conversation.user_id == user_id).first()
        if conversation:
            return conversation
    conversation = Conversation(user_id=user_id, title=default_title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.post("/documents/{document_id}/summarize")
def summarize_document(document_id: str, conversation_id: str | None = None, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    document = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "ready":
        raise HTTPException(status_code=400, detail="Document is not ready yet")

    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
        .all()
    )
    if not chunks:
        raise HTTPException(status_code=400, detail="Document has no content to summarize")

    chunk_contents = [c.content for c in chunks]
    summary = map_reduce_summarize(chunk_contents)

    conversation = _get_or_create_conversation(db, conversation_id, user_id, f"Summary of {document.filename}")
    db.add(Message(conversation_id=conversation.id, role="user", content=f"Summarize {document.filename}"))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=summary))
    db.commit()

    return {"document_id": document_id, "filename": document.filename, "summary": summary, "conversation_id": conversation.id}


@router.post("/documents/{document_id}/analyze")
def analyze_document_route(document_id: str, mode: str, conversation_id: str | None = None, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    if mode not in ("key_points", "questions", "simplify"):
        raise HTTPException(status_code=400, detail="Invalid mode")

    document = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "ready":
        raise HTTPException(status_code=400, detail="Document is not ready yet")

    chunks = (
        db.query(Chunk)
        .filter(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
        .all()
    )
    if not chunks:
        raise HTTPException(status_code=400, detail="Document has no content to analyze")

    chunk_contents = [c.content for c in chunks]
    result = analyze_document(mode, chunk_contents)

    conversation = _get_or_create_conversation(db, conversation_id, user_id, f"{ANALYZE_LABELS[mode]} {document.filename}")
    db.add(Message(conversation_id=conversation.id, role="user", content=f"{ANALYZE_LABELS[mode]} {document.filename}"))
    db.add(Message(conversation_id=conversation.id, role="assistant", content=result))
    db.commit()

    return {"document_id": document_id, "filename": document.filename, "result": result, "conversation_id": conversation.id}