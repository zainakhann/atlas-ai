from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User

router = APIRouter()


class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/auth/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(400, "Email already registered")

    user = User(email=request.email, hashed_password=hash_password(request.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}


DEMO_EMAIL = "demo@atlasai.local"
PROTECTED_DEMO_FILENAME = "octopus_intelligence.pdf"


@router.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not user.hashed_password or not verify_password(request.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")

    if user.email == DEMO_EMAIL:
        _reset_demo_account(user.id, db)

    token = create_access_token({"sub": user.id})
    return {"access_token": token, "token_type": "bearer"}


def _reset_demo_account(user_id: str, db: Session):
    from app.models.document import Document
    from app.models.conversation import Conversation
    from app.services.bm25_search import build_bm25_index
    from app.services.embeddings import embed_texts
    from app.services.vector_store import reset_index, add_vectors
    from app.models.document import Chunk

    stray_docs = (
        db.query(Document)
        .filter(Document.user_id == user_id, Document.filename != PROTECTED_DEMO_FILENAME)
        .all()
    )
    for doc in stray_docs:
        db.delete(doc)

    db.query(Conversation).filter(Conversation.user_id == user_id).delete()
    db.commit()

    all_chunks = db.query(Chunk).all()
    chunk_dicts = [
        {
            "chunk_id": str(c.id),
            "document_id": str(c.document_id),
            "page_number": c.page_number,
            "content": c.content,
        }
        for c in all_chunks
    ]
    build_bm25_index(chunk_dicts)
    reset_index()
    if chunk_dicts:
        contents = [c["content"] for c in chunk_dicts]
        vectors = embed_texts(contents)
        add_vectors(vectors, chunk_dicts)