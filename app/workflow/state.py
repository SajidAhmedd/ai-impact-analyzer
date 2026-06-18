"""
Workflow state definition.

This TypedDict defines ALL data that flows through the workflow.
Every node can read from and write to this state.

WHY EXPLICIT STATE:
- Clear contract between nodes
- Easy to debug (inspect state at any point)
- Type safety
- Enables parallel execution
"""

from typing import TypedDict, List, Optional, Any
from datetime import datetime


class AnalysisState(TypedDict, total=False):
    """
    State that flows through the entire analysis workflow.

    total=False means all fields are optional (not all nodes fill all fields)
    """

    # === INPUT ===
    change_request: str  # The change to analyze

    # === RETRIEVAL ===
    retrieved_docs: List[dict]  # Documents retrieved from RAG
    retrieval_query: str  # Query used for retrieval

    # === ANALYSIS OUTPUTS ===
    technical_analysis: Optional[dict]  # From technical reviewer
    operational_analysis: Optional[dict]  # From operational reviewer
    risk_analysis: Optional[dict]  # From risk assessor

    # === FINAL OUTPUT ===
    final_assessment: Optional[dict]  # Synthesized result
    recommendations: List[str]  # Action items

    # === METADATA ===
    confidence_score: float  # Overall confidence (0-1)
    execution_trace: List[dict]  # For observability
    errors: List[str]  # Any errors encountered

    # === TIMESTAMPS ===
    started_at: str
    completed_at: str