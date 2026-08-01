"""
Run once to create the shared demo account and upload a starter document.
Usage: python scripts/seed_demo.py
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.document import Document, Chunk
from app.models import workspace  # noqa: F401 — needed so SQLAlchemy can resolve Document.workspace_id FK
from app.services.document_processor import extract_pages, clean_text, chunk_text

DEMO_EMAIL = "demo@atlasai.local"
DEMO_PASSWORD = "atlas-demo-2026"
DEMO_PDF_PATH = "data/uploads/octopus_intelligence.pdf"  # place the PDF here first
UPLOAD_DIR = "data/uploads"

db = SessionLocal()

existing = db.query(User).filter(User.email == DEMO_EMAIL).first()
if existing:
    user = existing
    print(f"Demo user already exists: {user.id}")
else:
    user = User(email=DEMO_EMAIL, hashed_password=hash_password(DEMO_PASSWORD))
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"Created demo user: {user.id}")

already_has_docs = db.query(Document).filter(Document.user_id == user.id).first()
if already_has_docs:
    print("Demo user already has documents — skipping upload")
    db.close()
    exit()

if not os.path.exists(DEMO_PDF_PATH):
    print(f"ERROR: put octopus_intelligence.pdf at {DEMO_PDF_PATH} first")
    db.close()
    exit()

filename = "octopus_intelligence.pdf"
dest_path = os.path.join(UPLOAD_DIR, filename)
if os.path.abspath(DEMO_PDF_PATH) != os.path.abspath(dest_path):
    shutil.copyfile(DEMO_PDF_PATH, dest_path)

document = Document(filename=filename, status="processing", user_id=user.id)
db.add(document)
db.commit()
db.refresh(document)

pages = extract_pages(dest_path)
chunk_index = 0
for page_number, raw_text in pages:
    cleaned = clean_text(raw_text)
    if not cleaned:
        continue
    for chunk_content in chunk_text(cleaned):
        db.add(Chunk(document_id=document.id, content=chunk_content, chunk_index=chunk_index, page_number=page_number))
        chunk_index += 1

document.status = "ready"
db.commit()
print(f"Uploaded demo document: {chunk_index} chunks")
db.close()