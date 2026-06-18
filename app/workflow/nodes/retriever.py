
"""
Retriever node - fetches relevant documents for analysis.

This is the first node in the workflow. It takes the change request
and retrieves relevant context from the document store.
"""

from datetime import datetime
import structlog

from app.workflow.state import AnalysisState
from app.rag.retriever import get_retriever

logger = structlog.get_logger()


def retrieve_documents(state: AnalysisState) -> AnalysisState:
    """
    Retrieve relevant documents based on the change request.

    Input state:
        - change_request: The change to analyze

    Output state:
        - retrieved_docs: List of relevant document chunks
        - retrieval_query: The query used
        - execution_trace: Updated with this step
    """
    change_request = state.get("change_request", "")

    logger.info("Retrieving documents", query=change_request[:50])

    start_time = datetime.utcnow()

    # Get retriever and fetch documents
    retriever = get_retriever(k=5)
    docs = retriever.retrieve(change_request)
    docs = retriever.add_retrieval_explanation(docs, change_request)

    # Convert to serializable format
    retrieved_docs = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
        }
        for doc in docs
    ]

    end_time = datetime.utcnow()
    latency_ms = (end_time - start_time).total_seconds() * 1000

    # Update execution trace
    trace = state.get("execution_trace", [])
    trace.append({
        "node": "retriever",
        "timestamp": start_time.isoformat(),
        "latency_ms": latency_ms,
        "docs_retrieved": len(retrieved_docs),
    })

    logger.info(
        "Documents retrieved",
        count=len(retrieved_docs),
        latency_ms=latency_ms
    )

    return {
        **state,
        "retrieved_docs": retrieved_docs,
        "retrieval_query": change_request,
        "execution_trace": trace,
    }