"""Adapter between Streamlit and the backend's real inference service.

Keeping this as a thin wrapper means the demo uses exactly the same model
loading, preprocessing, risk mapping, and SHAP logic as the FastAPI backend.
Only presentation-only extras (per-class probabilities for the chart) are
computed here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Imported after the path adjustment so `app.*` resolves without installing the
# backend as a package. These imports are intentionally limited to modules that
# do not require a database or FastAPI.
from app.services.inference_service import (  # noqa: E402
    FEATURE_ORDER,
    get_registry,
    predict_for_student,
    risk_level_from_category,
)

__all__ = [
    "FEATURE_ORDER",
    "load_registry",
    "predict",
    "risk_level_from_category",
]


@st.cache_resource(show_spinner="Loading trained models…")
def load_registry():
    """Load the production registry once per Streamlit process."""
    return get_registry()


def predict(feature_dict: dict) -> dict:
    """Return the backend prediction plus per-class probabilities for charts."""
    registry = load_registry()

    result = predict_for_student(feature_dict)

    transformed = registry.preprocessor.transform(registry.to_feature_frame(feature_dict))
    probabilities = registry.classification_model.predict_proba(transformed)[0]
    result["classification"]["probabilities"] = [
        {"category": label, "probability": round(float(probability), 4)}
        for label, probability in zip(registry.class_labels, probabilities, strict=True)
    ]

    return result
