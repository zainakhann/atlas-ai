from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models.workspace import Workspace
from app.models.document import Document

router = APIRouter()


class WorkspaceCreate(BaseModel):
    name: str


class AssignDocumentsRequest(BaseModel):
    document_ids: list[str]


@router.post("/workspaces")
def create_workspace(request: WorkspaceCreate, db: Session = Depends(get_db)):
    workspace = Workspace(name=request.name)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return {"id": workspace.id, "name": workspace.name}


@router.get("/workspaces")
def list_workspaces(db: Session = Depends(get_db)):
    workspaces = db.query(Workspace).order_by(Workspace.created_at.desc()).all()
    return [{"id": w.id, "name": w.name} for w in workspaces]


@router.post("/workspaces/{workspace_id}/documents")
def assign_documents(workspace_id: str, request: AssignDocumentsRequest, db: Session = Depends(get_db)):
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(404, "Workspace not found")

    documents = db.query(Document).filter(Document.id.in_(request.document_ids)).all()
    for doc in documents:
        doc.workspace_id = workspace_id
    db.commit()

    return {"workspace_id": workspace_id, "assigned_count": len(documents)}


@router.get("/workspaces/{workspace_id}/documents")
def get_workspace_documents(workspace_id: str, db: Session = Depends(get_db)):
    documents = db.query(Document).filter(Document.workspace_id == workspace_id).all()
    return [{"id": d.id, "filename": d.filename, "status": d.status} for d in documents]