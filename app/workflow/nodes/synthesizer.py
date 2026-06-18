"""
Synthesizer Node.

Combines all analyses into a final assessment with:
- Executive summary
- Prioritized recommendations
- Overall confidence score
- Go/No-Go recommendation
"""

from datetime import datetime
import json
import structlog

from langchain_core.prompts import ChatPromptTemplate

from app.workflow.state import AnalysisState
from app.core.llm import get_llm
from app.prompts import load_prompt
from app.utils.json_parser import parse_json_safely

logger = structlog.get_logger()


SYNTHESIZER_PROMPT = load_prompt("synthesizer")


def calculate_confidence(state: AnalysisState) -> float:
    """
    Calculate confidence score based on analysis quality.

    Factors:
    - Retrieved docs quality (did we find relevant context?)
    - Parse success (did all analyses parse correctly?)
    - Completeness (did all analyses return data?)
    """
    score = 1.0

    # Check retrieved docs
    docs = state.get("retrieved_docs", [])
    if not docs:
        score -= 0.3  # No context is a big penalty
    elif len(docs) < 3:
        score -= 0.1  # Limited context

    # Check technical analysis
    tech = state.get("technical_analysis", {})
    if tech.get("error") or tech.get("parse_error"):
        score -= 0.2
    elif not tech.get("affected_systems"):
        score -= 0.1

    # Check operational analysis
    ops = state.get("operational_analysis", {})
    if ops.get("error") or ops.get("parse_error"):
        score -= 0.2

    # Check risk analysis
    risk = state.get("risk_analysis", {})
    if risk.get("error") or risk.get("parse_error"):
        score -= 0.2

    return max(0.1, min(1.0, score))


def synthesize_results(state: AnalysisState) -> AnalysisState:
    """
    Synthesize all analyses into final recommendations.
    """
    change_request = state.get("change_request", "")
    technical = state.get("technical_analysis", {})
    operational = state.get("operational_analysis", {})
    risk = state.get("risk_analysis", {})

    logger.info("Synthesizing results")

    start_time = datetime.utcnow()

    # Format analyses for prompt
    tech_str = json.dumps(technical, indent=2) if technical else "No technical analysis available"
    ops_str = json.dumps(operational, indent=2) if operational else "No operational analysis available"
    risk_str = json.dumps(risk, indent=2) if risk else "No risk analysis available"

    prompt = ChatPromptTemplate.from_template(SYNTHESIZER_PROMPT)
    llm = get_llm()
    chain = prompt | llm

    try:
        response = chain.invoke({
            "change_request": change_request,
            "technical_analysis": tech_str,
            "operational_analysis": ops_str,
            "risk_analysis": risk_str,
        })

        response_text = response.content if hasattr(response, 'content') else str(response)

        # Parse JSON with robust parser
        default_result = {
            "executive_summary": "Synthesis could not be completed.",
            "overall_impact_level": "unknown",
            "recommendation": "reconsider",
            "recommendation_rationale": "Analysis parsing failed",
            "prioritized_actions": [],
            "key_risks_summary": [],
            "success_factors": [],
            "estimated_effort": "unknown",
            "confidence_score": 0.3,
            "confidence_rationale": "Parse error occurred"
        }
        synthesis = parse_json_safely(response_text, default_result)

    except Exception as e:
        logger.error("Synthesis failed", error=str(e))
        synthesis = {
            "executive_summary": f"Synthesis failed: {str(e)}",
            "overall_impact_level": "unknown",
            "recommendation": "reconsider",
            "recommendation_rationale": str(e),
            "prioritized_actions": [],
            "key_risks_summary": [],
            "success_factors": [],
            "estimated_effort": "unknown",
            "confidence_score": 0.1,
            "confidence_rationale": "Error occurred",
            "error": True
        }

    # Calculate our own confidence score and compare
    calculated_confidence = calculate_confidence(state)
    synthesis["calculated_confidence"] = calculated_confidence

    end_time = datetime.utcnow()
    latency_ms = (end_time - start_time).total_seconds() * 1000

    # Update trace
    trace = state.get("execution_trace", [])
    trace.append({
        "node": "synthesizer",
        "timestamp": start_time.isoformat(),
        "latency_ms": latency_ms,
        "model": "llama3",
    })

    # Build recommendations list
    recommendations = []
    for action in synthesis.get("prioritized_actions", []):
        recommendations.append(action.get("action", ""))

    logger.info(
        "Synthesis complete",
        recommendation=synthesis.get("recommendation"),
        confidence=synthesis.get("confidence_score"),
        latency_ms=latency_ms
    )

    return {
        **state,
        "final_assessment": synthesis,
        "recommendations": recommendations,
        "confidence_score": synthesis.get("confidence_score", calculated_confidence),
        "execution_trace": trace,
    }