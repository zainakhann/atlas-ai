import os
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.logging_config import logger
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.core.security import get_current_user_id
from app.models.document import Document, Chunk
from app.services.document_processor import extract_pages, clean_text, chunk_text
from app.services.summarizer import compare_documents

router = APIRouter()
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    allowed = (".pdf", ".docx", ".txt", ".md")
    if not file.filename.lower().endswith(allowed):
        raise HTTPException(400, f"Unsupported file type. Allowed: {allowed}")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    document = Document(filename=file.filename, status="processing", user_id=user_id)
    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        pages = extract_pages(file_path)
        chunk_index = 0
        for page_number, raw_text in pages:
            cleaned = clean_text(raw_text)
            if not cleaned:
                continue
            page_chunks = chunk_text(cleaned)
            for chunk_content in page_chunks:
                chunk = Chunk(
                    document_id=document.id,
                    content=chunk_content,
                    chunk_index=chunk_index,
                    page_number=page_number,
                )
                db.add(chunk)
                chunk_index += 1

        document.status = "ready"
        db.commit()
        logger.info(f"Document uploaded successfully: {file.filename} ({chunk_index} chunks)")
    except Exception as e:
        document.status = "failed"
        db.commit()
        logger.error(f"Document processing failed: {file.filename} - {str(e)}")
        raise HTTPException(500, f"Processing failed: {str(e)}")

    return {
        "document_id": document.id,
        "filename": document.filename,
        "status": document.status,
        "chunk_count": chunk_index,
    }


@router.get("/documents")
def list_documents(db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    documents = db.query(Document).filter(Document.user_id == user_id).order_by(Document.id.desc()).all()
    results = []
    for doc in documents:
        chunk_count = db.query(func.count(Chunk.id)).filter(Chunk.document_id == doc.id).scalar()
        results.append({
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "chunk_count": chunk_count,
        })
    return results


@router.delete("/documents/{document_id}")
def delete_document(document_id: str, db: Session = Depends(get_db), user_id: str = Depends(get_current_user_id)):
    from app.services.bm25_search import build_bm25_index

    document = db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()
    if not document:
        raise HTTPException(404, "Document not found")

    file_path = os.path.join(UPLOAD_DIR, document.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(document)  # cascades to chunks via the relationship's cascade="all, delete-orphan"
    db.commit()

    remaining_chunks = db.query(Chunk).all()
    chunk_dicts = [
        {
            "chunk_id": str(c.id),
            "document_id": str(c.document_id),
            "page_number": c.page_number,
            "content": c.content,
        }
        for c in remaining_chunks
    ]
    build_bm25_index(chunk_dicts)
    logger.info(f"Document deleted: {document.filename}")

    return {"deleted": True, "document_id": document_id}





@router.post("/documents/compare")
def compare_two_documents(document_ids: list[str], db: Session = Depends(get_db)):
    if len(document_ids) != 2:
        raise HTTPException(400, "Provide exactly 2 document_ids to compare")

    results = {}
    for doc_id in document_ids:
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise HTTPException(404, f"Document {doc_id} not found")
        chunks = (
            db.query(Chunk)
            .filter(Chunk.document_id == doc_id)
            .order_by(Chunk.chunk_index.asc())
            .all()
        )
        summary = map_reduce_summarize([c.content for c in chunks])
        results[doc_id] = {"filename": document.filename, "summary": summary}

    doc_a, doc_b = document_ids
    comparison = compare_documents(
        results[doc_a]["filename"], results[doc_a]["summary"],
        results[doc_b]["filename"], results[doc_b]["summary"],
    )

    return {
        "document_a": results[doc_a],
        "document_b": results[doc_b],
        "comparison": comparison,
    }