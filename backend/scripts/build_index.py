import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.database import SessionLocal
from app.models.document import Chunk
from app.services.embeddings import embed_texts
from app.services.vector_store import add_vectors

def main():
    db = SessionLocal()
    chunks = db.query(Chunk).all()
    print(f"Found {len(chunks)} chunks in Postgres")

    if not chunks:
        print("No chunks found — upload a document first.")
        return

    texts = [c.content for c in chunks]
    metadatas = [
        {
            "chunk_id": str(c.id),
            "document_id": str(c.document_id),
            "chunk_index": c.chunk_index,
            "page_number": c.page_number,
            "content": c.content,
        }
        for c in chunks
    ]

    print("Generating embeddings...")
    vectors = embed_texts(texts)

    print("Adding to FAISS index...")
    add_vectors(vectors, metadatas)

    print(f"Done. Index now has vectors for {len(chunks)} chunks.")

    db.close()

if __name__ == "__main__":
    main()