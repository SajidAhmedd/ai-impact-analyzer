"""
Health check endpoints.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.llm import check_llm_connection
from app.core.embeddings import check_embeddings_connection
from app.core.vectorstore import get_collection_stats

router = APIRouter(prefix="/health", tags=["Health"])


class HealthStatus(BaseModel):
    status: str
    llm: bool
    embeddings: bool
    vectorstore: bool
    document_count: int


@router.get("", response_model=HealthStatus)
async def health_check():
    """Check the health of all system components."""
    llm_ok = check_llm_connection()
    embeddings_ok = check_embeddings_connection()

    try:
        stats = get_collection_stats()
        vectorstore_ok = True
        doc_count = stats.get("count", 0)
    except:
        vectorstore_ok = False
        doc_count = 0

    all_ok = llm_ok and embeddings_ok and vectorstore_ok

    return HealthStatus(
        status="healthy" if all_ok else "degraded",
        llm=llm_ok,
        embeddings=embeddings_ok,
        vectorstore=vectorstore_ok,
        document_count=doc_count
    )


@router.get("/ready")
async def readiness_check():
    """Simple readiness probe."""
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """Simple liveness probe."""
    return {"alive": True}