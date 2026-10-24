"""
AI Change Impact Analyzer - Streamlit Frontend
"""

import os
import sys
sys.path.insert(0, ".")

import streamlit as st
import requests
import json
from datetime import datetime

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "dev-api-key-change-in-production")

def get_headers():
    return {"X-API-Key": API_KEY}

st.set_page_config(page_title="AI Change Impact Analyzer", page_icon="◇", layout="wide")
st.title("AI Change Impact Analyzer")
st.caption("Analyze business and policy changes to predict technical, operational, and risk impacts")
st.divider()

with st.sidebar:
    st.header("Document Management")
    try:
        response = requests.get(f"{API_URL}/health/live", timeout=2)
        if response.status_code == 200:
            st.success("API Connected")
        else:
            st.error("API Error")
    except:
        st.error("API Not Available")
        st.caption("Make sure FastAPI is running on port 8000")
    st.divider()
    st.caption("Built with LangGraph + FastAPI + ChromaDB")

st.header("Enter Change Request")

# Example policy changes
st.subheader("Quick Examples")
st.caption("Click any example to analyze it:")

examples = [
    "Increase refund approval threshold from $100 to $500",
    "Migrate user authentication from session-based to JWT tokens",
    "Implement mandatory two-factor authentication for all employees",
    "Change data retention policy from 7 years to 5 years",
    "Allow remote work for all employees 3 days per week",
]

cols = st.columns(2)
for i, example in enumerate(examples):
    with cols[i % 2]:
        if st.button(example, key=f"example_{i}", use_container_width=True):
            st.session_state.selected_example = example

st.divider()

# Text area with selected example or empty
default_text = st.session_state.get("selected_example", "")
change_request = st.text_area(
    "Or describe your own policy change:",
    value=default_text,
    placeholder="Example: Increase refund threshold from $100 to $500.",
    height=100
)

analyze_button = st.button("Analyze Impact", type="primary", disabled=not change_request)

if analyze_button and change_request:
    # Clear the selected example after analysis starts
    if "selected_example" in st.session_state:
        del st.session_state.selected_example
    
    st.divider()
    st.header("Analysis Results")
    with st.spinner("Analyzing change impact... This may take 1-2 minutes."):
        try:
            response = requests.post(
                f"{API_URL}/analysis/run",
                json={"change_request": change_request},
                headers=get_headers(),
                timeout=300
            )
            if response.status_code == 200:
                result = response.json()
                st.session_state.last_result = result
            else:
                st.error(f"Analysis failed: {response.text}")
                st.stop()
        except requests.exceptions.Timeout:
            st.error("Analysis timed out. Please try again.")
            st.stop()
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.stop()
    
    result = st.session_state.get("last_result", {})
    synthesis = result.get("final_assessment", {})
    
    if synthesis:
        st.subheader("Executive Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            rec = synthesis.get("recommendation", "unknown")
            st.metric("Recommendation", rec.replace("_", " ").title())
        with col2:
            impact = synthesis.get("overall_impact_level", "unknown")
            st.metric("Impact Level", str(impact).title())
        with col3:
            effort = synthesis.get("estimated_effort", "unknown")
            st.metric("Effort", str(effort).title())
        
        summary = synthesis.get("executive_summary", "No summary available")
        st.info(summary)
        st.divider()
    
    tab1, tab2, tab3, tab4 = st.tabs(["Technical", "Operational", "Risk", "Full Details"])
    
    with tab1:
        tech = result.get("technical_analysis", {})
        if tech:
            st.markdown("**Summary:**")
            st.info(tech.get("summary", "No technical analysis available"))
            systems = tech.get("affected_systems", [])
            if systems:
                st.markdown("**Affected Systems:** " + ", ".join(str(s) for s in systems))
        else:
            st.warning("No technical analysis available")
    
    with tab2:
        ops = result.get("operational_analysis", {})
        if ops:
            st.markdown("**Summary:**")
            st.info(ops.get("summary", "No operational analysis available"))
            workflows = ops.get("affected_workflows", [])
            if workflows:
                st.markdown("**Affected Workflows:** " + ", ".join(str(w) for w in workflows))
        else:
            st.warning("No operational analysis available")
    
    with tab3:
        risk = result.get("risk_analysis", {})
        if risk:
            st.markdown("**Summary:**")
            st.info(risk.get("summary", "No risk analysis available"))
            risks = risk.get("risks", [])
            if risks:
                st.markdown("**Identified Risks:**")
                for r in risks:
                    if isinstance(r, dict):
                        st.markdown(f"- {r.get('risk', r.get('description', str(r)))}")
                    else:
                        st.markdown(f"- {r}")
        else:
            st.warning("No risk analysis available")
    
    with tab4:
        st.json(result)
    
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        total_time = result.get("total_time_ms", 0)
        st.caption(f"Analysis completed in {total_time/1000:.1f} seconds")
    with col2:
        st.download_button(
            "Download Results (JSON)",
            json.dumps(result, indent=2, default=str),
            f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "application/json"
        )
