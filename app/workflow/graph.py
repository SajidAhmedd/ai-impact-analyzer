# """
# LangGraph workflow definition.

# This defines the flow of analysis:
# 1. Retrieve relevant documents
# 2. Run technical analysis (more agents added later)
# 3. Return results

# WHY LANGGRAPH:
# - Explicit state management
# - Easy to add more nodes (agents) later
# - Built-in parallel execution support
# - Great debugging/observability
# """

# from datetime import datetime
# from langgraph.graph import StateGraph, END
# import structlog

# from app.workflow.state import AnalysisState
# from app.workflow.nodes.retriever import retrieve_documents
# from app.workflow.nodes.technical import analyze_technical_impact

# logger = structlog.get_logger()


# def create_analysis_workflow():
#     """
#     Create the analysis workflow graph.

#     Current flow (MVP):
#         START → retrieve → technical → END

#     Future flow:
#         START → retrieve → [technical, operational, risk] → synthesize → END
#     """

#     # Create the graph with our state type
#     workflow = StateGraph(AnalysisState)

#     # Add nodes
#     workflow.add_node("retrieve", retrieve_documents)
#     workflow.add_node("technical", analyze_technical_impact)

#     # Define edges (flow)
#     workflow.set_entry_point("retrieve")
#     workflow.add_edge("retrieve", "technical")
#     workflow.add_edge("technical", END)

#     # Compile the graph
#     graph = workflow.compile()

#     logger.info("Analysis workflow created")

#     return graph


# def run_analysis(change_request: str) -> AnalysisState:
#     """
#     Run the full analysis workflow.

#     Args:
#         change_request: The change to analyze

#     Returns:
#         Complete analysis state with all results

#     Usage:
#         result = run_analysis("Increase refund threshold from $100 to $500")
#         print(result["technical_analysis"])
#     """
#     logger.info("Starting analysis", change=change_request[:50])

#     # Create initial state
#     initial_state: AnalysisState = {
#         "change_request": change_request,
#         "retrieved_docs": [],
#         "execution_trace": [],
#         "errors": [],
#         "started_at": datetime.utcnow().isoformat(),
#     }

#     # Create and run workflow
#     workflow = create_analysis_workflow()

#     # Execute
#     result = workflow.invoke(initial_state)

#     # Add completion timestamp
#     result["completed_at"] = datetime.utcnow().isoformat()

#     logger.info(
#         "Analysis complete",
#         trace_steps=len(result.get("execution_trace", []))
#     )

#     return result


## why was the update needed

"""
LangGraph workflow definition.

Flow:
    START -> retrieve -> [technical, operational, risk] (parallel) -> END
"""

from datetime import datetime
from langgraph.graph import StateGraph, END
import structlog

from app.workflow.state import AnalysisState
from app.workflow.nodes.retriever import retrieve_documents
from app.workflow.nodes.technical import analyze_technical_impact
from app.workflow.nodes.operational import analyze_operational_impact
from app.workflow.nodes.risk import assess_risks
from app.workflow.nodes.synthesizer import synthesize_results

logger = structlog.get_logger()


def create_analysis_workflow():
    """
    Create the analysis workflow graph.

    Flow:
        START -> retrieve -> technical -> operational -> risk -> synthesize -> END

    Note: Running sequentially for simplicity.
    Parallel execution can be added later.
    """

    workflow = StateGraph(AnalysisState)

    # Add nodes
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("technical", analyze_technical_impact)
    workflow.add_node("operational", analyze_operational_impact)
    workflow.add_node("risk", assess_risks)
    workflow.add_node("synthesize", synthesize_results)

    # Define edges (sequential flow)
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "technical")
    workflow.add_edge("technical", "operational")
    workflow.add_edge("operational", "risk")
    workflow.add_edge("risk", "synthesize")
    workflow.add_edge("synthesize", END)

    # Compile
    graph = workflow.compile()

    logger.info("Analysis workflow created with all agents")

    return graph


def run_analysis(change_request: str) -> AnalysisState:
    """
    Run the full analysis workflow.
    """
    logger.info("Starting full analysis", change=change_request[:50])

    initial_state: AnalysisState = {
        "change_request": change_request,
        "retrieved_docs": [],
        "execution_trace": [],
        "errors": [],
        "started_at": datetime.utcnow().isoformat(),
    }

    workflow = create_analysis_workflow()
    result = workflow.invoke(initial_state)
    result["completed_at"] = datetime.utcnow().isoformat()

    logger.info(
        "Full analysis complete",
        trace_steps=len(result.get("execution_trace", []))
    )

    return result