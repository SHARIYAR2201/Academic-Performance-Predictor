"""Prediction page: manual student profile -> category, risk, GPA, and SHAP."""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st

from streamlit_demo.model import FEATURE_ORDER, predict
from streamlit_demo.ui import (
    TREND_OPTIONS,
    contribution_chart,
    feature_label,
    probability_chart,
    risk_badge,
)

logger = logging.getLogger(__name__)

DEFAULTS: dict[str, object] = {
    "previous_gpa": 3.0,
    "previous_semester_gpa": 2.9,
    "attendance_percentage": 85.0,
    "quiz_avg": 78.0,
    "assignment_avg": 80.0,
    "midterm_score": 75.0,
    "project_score": 82.0,
    "lab_score": 88.0,
    "completed_courses": 12,
    "credit_load": 15,
    "trend_label": "Stable (0)",
}

PRESETS: dict[str, dict[str, object]] = {
    "Strong student": {
        "previous_gpa": 3.8,
        "previous_semester_gpa": 3.7,
        "attendance_percentage": 96.0,
        "quiz_avg": 92.0,
        "assignment_avg": 94.0,
        "midterm_score": 91.0,
        "project_score": 93.0,
        "lab_score": 95.0,
        "completed_courses": 20,
        "credit_load": 15,
        "trend_label": "Improving (+1)",
    },
    "Typical student": dict(DEFAULTS),
    "At-risk profile": {
        "previous_gpa": 2.1,
        "previous_semester_gpa": 1.9,
        "attendance_percentage": 55.0,
        "quiz_avg": 48.0,
        "assignment_avg": 52.0,
        "midterm_score": 45.0,
        "project_score": 50.0,
        "lab_score": 58.0,
        "completed_courses": 4,
        "credit_load": 18,
        "trend_label": "Declining (-1)",
    },
}


def _initialise_state() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)


def _apply_preset(values: dict[str, object]) -> None:
    for key, value in values.items():
        st.session_state[key] = value
    st.session_state.pop("prediction_result", None)
    st.session_state.pop("prediction_inputs", None)


def _render_results(result: dict) -> None:
    classification = result["classification"]
    regression = result["regression"]

    st.subheader("Prediction")
    col_gpa, col_category, col_risk, col_confidence = st.columns(4)
    col_gpa.metric("Predicted GPA", f"{regression['predicted_gpa']:.2f}", help="Model estimate on a 0.0–4.0 scale")
    col_category.metric("Performance category", classification["predicted_category"])
    col_risk.metric("Risk level", classification["risk_level"])
    col_confidence.metric("Confidence", f"{classification['confidence'] * 100:.0f}%", help="The model's own predicted-class probability")

    st.markdown(risk_badge(classification["risk_level"]), unsafe_allow_html=True)
    st.caption(
        f"Classification model: `{classification['model_version']}` · "
        f"Regression model: `{regression['model_version']}`"
    )

    st.divider()

    st.subheader("Probability across performance categories")
    probability = probability_chart(classification.get("probabilities", []), classification["predicted_category"])
    if probability is not None:
        st.altair_chart(probability, width="stretch")

    st.subheader("Why the model reached this result")
    st.caption(
        "Positive (green) contributions pushed the prediction up; negative (red) contributions "
        "pushed it down. These describe this model's behaviour for this input — they are not proof "
        "of real-world cause and effect."
    )

    category_tab, gpa_tab = st.tabs(["Performance category", "Predicted GPA"])
    with category_tab:
        chart = contribution_chart(classification["explanation"])
        if chart is not None:
            st.altair_chart(chart, width="stretch")
        else:
            st.info("This model type does not provide a fast SHAP explanation, so none is shown.")

    with gpa_tab:
        chart = contribution_chart(regression["explanation"])
        if chart is not None:
            st.altair_chart(chart, width="stretch")
        else:
            st.info("This model type does not provide a fast SHAP explanation, so none is shown.")

    with st.expander("View all SHAP contributions"):
        rows = [
            {
                "Feature": feature_label(item["feature"]),
                "Category contribution": next(
                    (
                        contribution["contribution"]
                        for contribution in classification["explanation"]
                        if contribution["feature"] == item["feature"]
                    ),
                    None,
                ),
                "GPA contribution": next(
                    (
                        contribution["contribution"]
                        for contribution in regression["explanation"]
                        if contribution["feature"] == item["feature"]
                    ),
                    None,
                ),
            }
            for item in classification["explanation"] or regression["explanation"]
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.warning(
        "This prediction is a model-generated estimate based on historical and current academic "
        "data. It is not a certainty and must not be the sole basis for academic, disciplinary, or "
        "admissions decisions. Feature contributions describe the model's behaviour, not proven "
        "real-world causes."
    )


def render() -> None:
    st.title("Academic performance prediction")
    st.markdown(
        "Enter a student's academic profile to get a **performance-category estimate**, an "
        "**early-warning risk level**, a **predicted GPA**, and the **SHAP feature contributions** "
        "behind each result."
    )
    st.info(
        "Standalone demo: no student records are read or stored. The full system uses a FastAPI "
        "backend, PostgreSQL, and role-based access control."
    )

    _initialise_state()

    st.caption("Start from an example profile, then adjust the inputs:")
    preset_columns = st.columns(len(PRESETS))
    for column, (name, values) in zip(preset_columns, PRESETS.items(), strict=True):
        with column:
            if st.button(name, width="stretch"):
                _apply_preset(values)
                st.rerun()

    with st.form("prediction_form", border=True):
        st.subheader("Academic history")
        history_left, history_right, history_trend = st.columns(3)
        with history_left:
            st.slider("Previous GPA", 0.0, 4.0, step=0.01, format="%.2f", key="previous_gpa")
        with history_right:
            st.slider(
                "Previous semester GPA",
                0.0,
                4.0,
                step=0.01,
                format="%.2f",
                key="previous_semester_gpa",
            )
        with history_trend:
            st.selectbox("Historical trend", list(TREND_OPTIONS), key="trend_label")

        st.subheader("Current semester")
        current_left, current_middle, current_right = st.columns(3)
        with current_left:
            st.slider("Attendance %", 0.0, 100.0, step=1.0, format="%.0f", key="attendance_percentage")
            st.slider("Quiz average", 0.0, 100.0, step=1.0, format="%.0f", key="quiz_avg")
        with current_middle:
            st.slider("Assignment average", 0.0, 100.0, step=1.0, format="%.0f", key="assignment_avg")
            st.slider("Midterm score", 0.0, 100.0, step=1.0, format="%.0f", key="midterm_score")
        with current_right:
            st.slider("Project score", 0.0, 100.0, step=1.0, format="%.0f", key="project_score")
            st.slider("Lab score", 0.0, 100.0, step=1.0, format="%.0f", key="lab_score")

        st.subheader("Enrollment")
        enrollment_left, enrollment_right = st.columns(2)
        with enrollment_left:
            st.number_input("Completed courses", min_value=0, max_value=60, step=1, key="completed_courses")
        with enrollment_right:
            st.number_input("Credit load this semester", min_value=0, max_value=24, step=1, key="credit_load")

        submitted = st.form_submit_button("Generate prediction", type="primary", width="stretch")

    if submitted:
        features = {
            feature: float(st.session_state[feature])
            for feature in FEATURE_ORDER
            if feature not in {"completed_courses", "credit_load", "historical_trend"}
        }
        features["completed_courses"] = int(st.session_state["completed_courses"])
        features["credit_load"] = int(st.session_state["credit_load"])
        features["historical_trend"] = TREND_OPTIONS[st.session_state["trend_label"]]

        with st.spinner("Running model inference and SHAP explanation…"):
            try:
                st.session_state["prediction_result"] = predict(features)
                st.session_state["prediction_inputs"] = features
            except Exception:  # pragma: no cover - surfaced in the UI
                logger.exception("Streamlit prediction failed")
                st.session_state.pop("prediction_result", None)
                st.session_state.pop("prediction_inputs", None)
                st.error(
                    "Could not generate a prediction. The model registry may be missing or "
                    "incompatible with the installed ML packages. Check the app logs for details."
                )

    result = st.session_state.get("prediction_result")
    if result is not None:
        _render_results(result)
