"""
Technical Analysis Node.

Analyzes the TECHNICAL impacts of a change:
- Affected systems
- Dependencies
- API changes
- Migration requirements
"""

from datetime import datetime
from typing import List
import structlog

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from app.workflow.state import AnalysisState
from app.core.llm import get_llm
from app.prompts import load_prompt
from app.utils.json_parser import parse_json_safely

logger = structlog.get_logger()


# === STRUCTURED OUTPUT SCHEMA ===

class TechnicalImpact(BaseModel):
    """A single technical impact."""
    system: str = Field(description="Name of affected system")
    impact_type: str = Field(description="Type: 'modification', 'integration', 'deprecation'")
    description: str = Field(description="Description of the impact")
    severity: str = Field(description="Severity: 'low', 'medium', 'high'")


class TechnicalAnalysisOutput(BaseModel):
    """Complete technical analysis output."""
    affected_systems: List[str] = Field(description="List of affected system names")
    impacts: List[TechnicalImpact] = Field(description="Detailed impacts")
    migration_required: bool = Field(description="Whether migration is needed")
    technical_debt_impact: str = Field(description="Impact on tech debt: 'reduces', 'neutral', 'increases'")
    summary: str = Field(description="Brief summary of technical impacts")


# === PROMPT TEMPLATE ===
# Loaded from prompts/technical.txt for easier editing
TECHNICAL_PROMPT = load_prompt("technical")


def analyze_technical_impact(state: AnalysisState) -> AnalysisState:
    """
    Analyze technical impacts of the change.

    Input state:
        - change_request: The change to analyze
        - retrieved_docs: Context documents

    Output state:
        - technical_analysis: Structured analysis result
        - execution_trace: Updated
    """
    change_request = state.get("change_request", "")
    retrieved_docs = state.get("retrieved_docs", [])

    logger.info("Analyzing technical impact")

    start_time = datetime.utcnow()

    # Format context from retrieved documents
    context = "\n\n---\n\n".join([
        f"Source: {doc['metadata'].get('source', 'unknown')}\n{doc['content']}"
        for doc in retrieved_docs
    ]) if retrieved_docs else "No relevant documentation found."

    # Create prompt
    prompt = ChatPromptTemplate.from_template(TECHNICAL_PROMPT)

    # Get LLM and create chain
    llm = get_llm()
    chain = prompt | llm

    # Run analysis
    try:
        response = chain.invoke({
            "change_request": change_request,
            "context": context,
        })

        # Parse JSON with robust parser
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        default_result = {
            "affected_systems": [],
            "impacts": [],
            "migration_required": False,
            "technical_debt_impact": "neutral",
            "summary": "Analysis could not be parsed."
        }
        technical_analysis = parse_json_safely(response_text, default_result)

    except Exception as e:
        logger.error("Technical analysis failed", error=str(e))
        technical_analysis = {
            "affected_systems": [],
            "impacts": [],
            "migration_required": False,
            "technical_debt_impact": "neutral",
            "summary": f"Analysis failed: {str(e)}",
            "error": True
        }

    end_time = datetime.utcnow()
    latency_ms = (end_time - start_time).total_seconds() * 1000

    # Update execution trace
    trace = state.get("execution_trace", [])
    trace.append({
        "node": "technical_analyzer",
        "timestamp": start_time.isoformat(),
        "latency_ms": latency_ms,
        "model": "llama3",
    })

    logger.info(
        "Technical analysis complete",
        systems_affected=len(technical_analysis.get("affected_systems", [])),
        latency_ms=latency_ms
    )

    return {
        **state,
        "technical_analysis": technical_analysis,
        "execution_trace": trace,
    }