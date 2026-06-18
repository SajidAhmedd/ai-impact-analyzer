"""
Document management endpoints.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pathlib import Path
from pydantic import BaseModel

from app.ingestion.processor import process_document
from app.core.vectorstore import get_collection_stats, get_chroma_client
from app.auth import get_api_key

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
    dependencies=[Depends(get_api_key)]  # Require API key
)


class DocumentUploadResponse(BaseModel):
    success: bool
    filename: str
    chunks_created: int
    message: str


class CollectionStats(BaseModel):
    name: str
    total_documents: int


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form(default="other"),
    doc_type: str = Form(default="other"),
    criticality: str = Form(default="medium"),
):
    """Upload and process a document."""
    allowed_extensions = [".txt", ".md", ".pdf", ".docx"]
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Allowed: {allowed_extensions}"
        )

    temp_path = Path(f"data/documents/{file.filename}")
    temp_path.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    temp_path.write_bytes(content)

    try:
        metadata = {
            "department": department,
            "doc_type": doc_type,
            "criticality": criticality,
        }
        chunks = process_document(str(temp_path), metadata)

        return DocumentUploadResponse(
            success=True,
            filename=file.filename,
            chunks_created=chunks,
            message=f"Document processed into {chunks} chunks"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=CollectionStats)
async def get_stats():
    """Get vector store statistics."""
    try:
        stats = get_collection_stats()
        return CollectionStats(
            name=stats.get("name", "documents"),
            total_documents=stats.get("count", 0)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_documents():
    """Clear all documents from the vector store."""
    try:
        vectorstore = get_chroma_client()
        collection = vectorstore._collection

        all_ids = collection.get()["ids"]
        if all_ids:
            collection.delete(ids=all_ids)

        return {"success": True, "deleted_count": len(all_ids)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))