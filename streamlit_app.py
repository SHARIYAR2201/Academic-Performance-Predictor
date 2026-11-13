"""Streamlit Community Cloud entrypoint.

Run locally with:
    streamlit run streamlit_app.py
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Academic Performance Predictor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

from streamlit_demo.pages import about, dataset, performance, predict  # noqa: E402

CUSTOM_CSS = """
<style>
.block-container {
    max-width: 1180px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}
[data-testid="stMetricValue"] {
    font-size: 1.75rem;
}
.risk-badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 0.28rem 0.8rem;
    font-size: 0.85rem;
    font-weight: 600;
    margin-top: -0.4rem;
    margin-bottom: 0.5rem;
}
</style>
"""

PAGES = {
    "Prediction": predict.render,
    "Model performance": performance.render,
    "Dataset": dataset.render,
    "About": about.render,
}

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

with st.sidebar:
    st.title("🎓 Academic Predictor")
    st.caption("Explainable ML demo")
    selection = st.radio("Navigate", list(PAGES), label_visibility="collapsed")
    st.divider()
    st.info(
        "Standalone ML demo. No login, no stored records. "
        "The full system uses FastAPI + PostgreSQL + Next.js."
    )
    st.caption("Predictions are model-generated estimates — not academic decisions.")

PAGES[selection]()
