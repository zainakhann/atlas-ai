from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.logging_config import setup_logging, logger
from app.models import document, conversation, user, workspace
from app.models.document import Chunk
from app.routes import upload, chat, conversations, workspaces, auth, summarize
from app.services.bm25_search import build_bm25_index

setup_logging()

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-Id"],
)

app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(workspaces.router)
app.include_router(auth.router)
app.include_router(summarize.router)


@app.on_event("startup")
def build_search_indexes():
    db = SessionLocal()
    try:
        chunks = db.query(Chunk).all()
        chunk_dicts = [
            {
                "chunk_id": str(c.id),
                "document_id": str(c.document_id),
                "page_number": c.page_number,
                "content": c.content,
            }
            for c in chunks
        ]
        build_bm25_index(chunk_dicts)
        logger.info(f"BM25 index built with {len(chunk_dicts)} chunks")
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok", "app": settings.app_name}