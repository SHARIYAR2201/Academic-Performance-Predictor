"""Presentation helpers shared by the Streamlit pages."""
from __future__ import annotations

import altair as alt
import pandas as pd

FEATURE_LABELS: dict[str, str] = {
    "previous_gpa": "Previous GPA",
    "previous_semester_gpa": "Previous semester GPA",
    "attendance_percentage": "Attendance %",
    "quiz_avg": "Quiz average",
    "assignment_avg": "Assignment average",
    "midterm_score": "Midterm score",
    "project_score": "Project score",
    "lab_score": "Lab score",
    "completed_courses": "Completed courses",
    "credit_load": "Credit load",
    "historical_trend": "Historical trend",
    "final_gpa": "Final GPA",
    "performance_category": "Performance category",
}

TREND_OPTIONS: dict[str, int] = {
    "Improving (+1)": 1,
    "Stable (0)": 0,
    "Declining (-1)": -1,
}

RISK_META: dict[str, tuple[str, str, str]] = {
    "LOW": ("Low risk", "#ecfdf5", "#047857"),
    "MEDIUM": ("Medium risk", "#fffbeb", "#b45309"),
    "HIGH": ("High risk", "#fef2f2", "#b91c1c"),
}

CATEGORY_ORDER = ["At Risk", "Average", "Good", "Excellent"]


def feature_label(feature: str) -> str:
    return FEATURE_LABELS.get(feature, feature.replace("_", " ").title())


def risk_badge(level: str) -> str:
    label, background, foreground = RISK_META.get(level, (level, "#f1f5f9", "#334155"))
    return (
        f'<span class="risk-badge" style="background:{background};color:{foreground};'
        f'border:1px solid {foreground}33">{label}</span>'
    )


def contribution_chart(contributions: list[dict]) -> alt.Chart | None:
    """Horizontal SHAP bar chart: green pushes the prediction up, red down."""
    if not contributions:
        return None

    frame = pd.DataFrame(contributions).copy()
    frame["Feature"] = frame["feature"].map(feature_label)
    frame = frame.sort_values("contribution", ascending=True)

    return (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X("contribution:Q", title="SHAP contribution"),
            y=alt.Y("Feature:N", title=None, sort=None),
            color=alt.condition(
                alt.datum.contribution >= 0,
                alt.value("#059669"),
                alt.value("#dc2626"),
            ),
            tooltip=[
                alt.Tooltip("Feature:N", title="Feature"),
                alt.Tooltip("contribution:Q", title="Contribution", format=".4f"),
            ],
        )
        .properties(height=max(260, 30 * len(frame)))
    )


def probability_chart(probabilities: list[dict], predicted_category: str) -> alt.Chart | None:
    if not probabilities:
        return None

    frame = pd.DataFrame(probabilities)
    frame["Selected"] = frame["category"] == predicted_category

    bars = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("category:N", sort=CATEGORY_ORDER, title=None),
            y=alt.Y(
                "probability:Q",
                title="Probability",
                axis=alt.Axis(format="%"),
                scale=alt.Scale(domain=[0, 1]),
            ),
            color=alt.condition(
                alt.datum.Selected,
                alt.value("#0f172a"),
                alt.value("#94a3b8"),
            ),
            tooltip=[
                alt.Tooltip("category:N", title="Category"),
                alt.Tooltip("probability:Q", title="Probability", format=".1%"),
            ],
        )
    )
    labels = bars.mark_text(dy=-8, color="#334155").encode(
        text=alt.Text("probability:Q", format=".0%")
    )

    return (bars + labels).properties(height=260)


def confusion_matrix_chart(matrix: list[list[int]], labels: list[str]) -> alt.Chart:
    frame = pd.DataFrame(matrix, index=labels, columns=labels)
    long = frame.stack().rename("students").reset_index()
    long.columns = ["Actual", "Predicted", "Students"]
    threshold = long["Students"].max() / 2

    base = (
        alt.Chart(long)
        .mark_rect(stroke="#ffffff", strokeWidth=1)
        .encode(
            x=alt.X("Predicted:N", sort=labels, title="Predicted category"),
            y=alt.Y("Actual:N", sort=labels, title="Actual category"),
            color=alt.Color(
                "Students:Q",
                scale=alt.Scale(scheme="blues"),
                title="Students",
            ),
            tooltip=[
                alt.Tooltip("Actual:N"),
                alt.Tooltip("Predicted:N"),
                alt.Tooltip("Students:Q"),
            ],
        )
    )
    text = base.mark_text(baseline="middle", fontSize=13).encode(
        text=alt.Text("Students:Q"),
        color=alt.condition(
            alt.datum.Students > threshold,
            alt.value("#ffffff"),
            alt.value("#0f172a"),
        ),
    )

    return (base + text).properties(height=340)
