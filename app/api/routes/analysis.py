"""
Analysis endpoints.

Protected by API key authentication.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.workflow.graph import run_analysis
from app.auth import get_api_key

router = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
    dependencies=[Depends(get_api_key)]  # Require API key
)


class AnalysisRequest(BaseModel):
    change_request: str = Field(..., min_length=10, description="Description of the change")

    class Config:
        json_schema_extra = {
            "example": {
                "change_request": "Increase the refund approval threshold from $100 to $500"
            }
        }


class ExecutionStep(BaseModel):
    node: str
    timestamp: str
    latency_ms: float


class AnalysisResponse(BaseModel):
    change_request: str
    technical_analysis: Optional[Dict[str, Any]] = None
    operational_analysis: Optional[Dict[str, Any]] = None
    risk_analysis: Optional[Dict[str, Any]] = None
    final_assessment: Optional[Dict[str, Any]] = None
    retrieved_docs_count: int = 0
    execution_trace: List[ExecutionStep] = []
    started_at: str
    completed_at: str
    total_time_ms: float


@router.post("/run", response_model=AnalysisResponse)
async def analyze_change(request: AnalysisRequest):
    """
    Analyze a change request.

    Runs the full analysis pipeline with all agents.
    May take 2-3 minutes.
    """
    try:
        result = run_analysis(request.change_request)

        started = datetime.fromisoformat(result.get("started_at", ""))
        completed = datetime.fromisoformat(result.get("completed_at", ""))
        total_ms = (completed - started).total_seconds() * 1000

        trace = [
            ExecutionStep(
                node=step.get("node", "unknown"),
                timestamp=step.get("timestamp", ""),
                latency_ms=step.get("latency_ms", 0)
            )
            for step in result.get("execution_trace", [])
        ]

        return AnalysisResponse(
            change_request=request.change_request,
            technical_analysis=result.get("technical_analysis"),
            operational_analysis=result.get("operational_analysis"),
            risk_analysis=result.get("risk_analysis"),
            final_assessment=result.get("final_assessment"),
            retrieved_docs_count=len(result.get("retrieved_docs", [])),
            execution_trace=trace,
            started_at=result.get("started_at", ""),
            completed_at=result.get("completed_at", ""),
            total_time_ms=total_ms
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))