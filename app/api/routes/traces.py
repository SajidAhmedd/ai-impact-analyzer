"""
Trace endpoints for observability.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from app.observability.tracer import get_tracer
from app.auth import get_api_key

router = APIRouter(
    prefix="/traces",
    tags=["Traces"],
    dependencies=[Depends(get_api_key)]  # Require API key
)


@router.get("")
async def list_traces(limit: int = 10):
    """
    List recent execution traces.
    """
    tracer = get_tracer()
    return {"traces": tracer.list_traces(limit=limit)}


@router.get("/{trace_id}")
async def get_trace(trace_id: str):
    """
    Get a specific trace by ID.
    """
    tracer = get_tracer()
    trace = tracer.get_trace(trace_id)

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    return trace.to_dict()