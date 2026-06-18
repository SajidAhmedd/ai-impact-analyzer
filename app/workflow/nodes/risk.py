"""
Risk Assessment Node.

Analyzes the RISK implications of a change:
- Potential risks and their severity
- Likelihood of occurrence
- Mitigation strategies
- Compliance concerns
"""

from datetime import datetime
import structlog

from langchain_core.prompts import ChatPromptTemplate

from app.workflow.state import AnalysisState
from app.core.llm import get_llm
from app.prompts import load_prompt
from app.utils.json_parser import parse_json_safely

logger = structlog.get_logger()


RISK_PROMPT = load_prompt("risk")


def assess_risks(state: AnalysisState) -> AnalysisState:
    """
    Assess risks of the change.
    """
    change_request = state.get("change_request", "")
    retrieved_docs = state.get("retrieved_docs", [])

    logger.info("Assessing risks")

    start_time = datetime.utcnow()

    # Format context
    context = "\n\n---\n\n".join([
        f"Source: {doc['metadata'].get('source', 'unknown')}\n{doc['content']}"
        for doc in retrieved_docs
    ]) if retrieved_docs else "No relevant documentation found."

    # Create prompt and run
    prompt = ChatPromptTemplate.from_template(RISK_PROMPT)
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
            "risks": [],
            "overall_risk_level": "unknown",
            "compliance_concerns": [],
            "recommended_safeguards": [],
            "rollback_complexity": "unknown",
            "summary": "Analysis could not be parsed."
        }
        risk_analysis = parse_json_safely(response_text, default_result)

    except Exception as e:
        logger.error("Risk assessment failed", error=str(e))
        risk_analysis = {
            "risks": [],
            "overall_risk_level": "unknown",
            "compliance_concerns": [],
            "recommended_safeguards": [],
            "rollback_complexity": "unknown",
            "summary": f"Assessment failed: {str(e)}",
            "error": True
        }

    end_time = datetime.utcnow()
    latency_ms = (end_time - start_time).total_seconds() * 1000

    # Update trace
    trace = state.get("execution_trace", [])
    trace.append({
        "node": "risk_assessor",
        "timestamp": start_time.isoformat(),
        "latency_ms": latency_ms,
        "model": "llama3",
    })

    logger.info(
        "Risk assessment complete",
        risks_identified=len(risk_analysis.get("risks", [])),
        latency_ms=latency_ms
    )

    return {
        **state,
        "risk_analysis": risk_analysis,
        "execution_trace": trace,
    }