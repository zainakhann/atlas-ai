import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user_id
from app.models.document import Document
from app.models.conversation import Conversation, Message
from app.services.embeddings import embed_texts
from app.services.hybrid_search import hybrid_search, is_multi_document_query, per_document_hybrid_search
from app.services.reranker import rerank
from app.services.llm import generate_answer_stream, contextualize_query

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    top_k: int = 5
    conversation_id: str | None = None
    workspace_id: str | None = None


def _attach_filenames(chunks: list[dict], db: Session) -> list[dict]:
    document_ids = list({chunk["document_id"] for chunk in chunks})
    documents = db.query(Document).filter(Document.id.in_(document_ids)).all()
    filename_lookup = {str(doc.id): doc.filename for doc in documents}

    for chunk in chunks:
        chunk["filename"] = filename_lookup.get(chunk["document_id"], "Unknown document")

    return chunks


def _make_title_from_question(question: str, db: Session, max_length: int = 50) -> str:
    cleaned = question.strip()
    base_title = cleaned if len(cleaned) <= max_length else cleaned[:max_length].rsplit(" ", 1)[0] + "..."

    existing_titles = {
        row[0] for row in db.query(Conversation.title).filter(Conversation.title.like(f"{base_title}%")).all()
    }

    if base_title not in existing_titles:
        return base_title

    counter = 2
    while f"{base_title} ({counter})" in existing_titles:
        counter += 1
    return f"{base_title} ({counter})"


def sse_event_generator(question: str, top_k: int, conversation_id: str, workspace_id: str | None, user_id: str):
    db = SessionLocal()
    try:
        prior_messages = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        conversation_history = [
            {"role": m.role, "content": m.content} for m in prior_messages
        ][-10:]  # cap history length so prompts don't grow unbounded over a long chat

        db.add(Message(conversation_id=conversation_id, role="user", content=question))

        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conversation and conversation.title == "New Conversation":
            conversation.title = _make_title_from_question(question, db)

        db.commit()

        search_query = contextualize_query(question, conversation_history)
        query_vec = embed_texts([search_query])[0]

        doc_query = db.query(Document).filter(Document.status == "ready", Document.user_id == user_id)
        if workspace_id:
            doc_query = doc_query.filter(Document.workspace_id == workspace_id)
        scoped_documents = doc_query.all()
        document_ids = [str(doc.id) for doc in scoped_documents]
        document_filenames = [doc.filename for doc in scoped_documents]

        if is_multi_document_query(question, document_filenames):
            candidates = per_document_hybrid_search(search_query, query_vec, document_ids, top_k_per_doc=3)
            candidate_chunks = [metadata for metadata, score in candidates]
            reranked = rerank(search_query, candidate_chunks, top_k=top_k * 2)
            chunks = []
            for metadata, score in reranked:
                metadata["score"] = score
                chunks.append(metadata)
            print(f"[DEBUG] Question: {question!r}")
            print(f"[DEBUG] Reranked scores: {[round(s, 4) for _, s in reranked]}")
        else:
            candidates = hybrid_search(search_query, query_vec, top_k=20, candidate_k=20, allowed_document_ids=document_ids)
            candidate_chunks = [metadata for metadata, score in candidates]
            reranked = rerank(search_query, candidate_chunks, top_k=top_k)
            print(f"[DEBUG] Question: {question!r}")
            print(f"[DEBUG] Reranked scores: {[round(s, 4) for _, s in reranked]}")
            chunks = []
            for metadata, score in reranked:
                metadata["score"] = score
                chunks.append(metadata)

        chunks = _attach_filenames(chunks, db)

        full_answer = ""
        final_sources = []

        for event in generate_answer_stream(question, chunks, conversation_history):
            if event["type"] == "token":
                full_answer += event["content"]
            elif event["type"] == "sources":
                final_sources = event["sources"]
            yield f"data: {json.dumps(event)}\n\n"

        db.add(
            Message(
                conversation_id=conversation_id,
                role="assistant",
                content=full_answer,
                sources=final_sources,
            )
        )
        db.commit()
    finally:
        db.close()


@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    conversation_id = request.conversation_id
    if not conversation_id:
        conversation = Conversation(user_id=user_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        conversation_id = conversation.id

    return StreamingResponse(
        sse_event_generator(request.question, request.top_k, conversation_id, request.workspace_id, user_id),
        media_type="text/event-stream",
        headers={"X-Conversation-Id": conversation_id},
    )

