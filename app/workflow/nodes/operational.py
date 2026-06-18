"""
Operational Analysis Node.

Analyzes the OPERATIONAL impacts of a change:
- Affected workflows and processes
- Teams impacted
- Training requirements
- Process disruption level
"""

from datetime import datetime
import structlog

from langchain_core.prompts import ChatPromptTemplate

from app.workflow.state import AnalysisState
from app.core.llm import get_llm
from app.prompts import load_prompt
from app.utils.json_parser import parse_json_safely

logger = structlog.get_logger()


OPERATIONAL_PROMPT = load_prompt("operational")


def analyze_operational_impact(state: AnalysisState) -> AnalysisState:
    """
    Analyze operational impacts of the change.
    """
    change_request = state.get("change_request", "")
    retrieved_docs = state.get("retrieved_docs", [])

    logger.info("Analyzing operational impact")

    start_time = datetime.utcnow()

    # Format context
    context = "\n\n---\n\n".join([
        f"Source: {doc['metadata'].get('source', 'unknown')}\n{doc['content']}"
        for doc in retrieved_docs
    ]) if retrieved_docs else "No relevant documentation found."

    # Create prompt and run
    prompt = ChatPromptTemplate.from_template(OPERATIONAL_PROMPT)
    llm = get_llm()
    chain = prompt | llm

    try:
        response = chain.invoke({
            "change_request": change_request,
            "context": context,
        })

        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse JSON with robust parser
        default_result = {
            "affected_workflows": [],
            "teams_impacted": [],
            "process_changes": [],
            "training_required": False,
            "training_scope": "none",
            "disruption_level": "unknown",
            "implementation_considerations": [],
            "summary": "Analysis could not be parsed."
        }
        operational_analysis = parse_json_safely(response_text, default_result)

    except Exception as e:
        logger.error("Operational analysis failed", error=str(e))
        operational_analysis = {
            "affected_workflows": [],
            "teams_impacted": [],
            "process_changes": [],
            "training_required": False,
            "training_scope": "none",
            "disruption_level": "unknown",
            "implementation_considerations": [],
            "summary": f"Analysis failed: {str(e)}",
            "error": True
        }

    end_time = datetime.utcnow()
    latency_ms = (end_time - start_time).total_seconds() * 1000

    # Update trace
    trace = state.get("execution_trace", [])
    trace.append({
        "node": "operational_analyzer",
        "timestamp": start_time.isoformat(),
        "latency_ms": latency_ms,
        "model": "llama3",
    })

    logger.info(
        "Operational analysis complete",
        workflows_affected=len(operational_analysis.get("affected_workflows", [])),
        latency_ms=latency_ms
    )

    return {
        **state,
        "operational_analysis": operational_analysis,
        "execution_trace": trace,
    }