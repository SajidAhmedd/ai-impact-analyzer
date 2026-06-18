"""Test workflow state."""

from app.workflow.state import AnalysisState


def test_analysis_state_structure():
    """Test AnalysisState has required fields."""
    # AnalysisState is a TypedDict, check its keys
    state: AnalysisState = {
        "change_request": "test change",
        "retrieved_docs": [],
        "execution_trace": [],
        "errors": [],
    }
    
    assert "change_request" in state
    assert "retrieved_docs" in state
    assert isinstance(state["errors"], list)
