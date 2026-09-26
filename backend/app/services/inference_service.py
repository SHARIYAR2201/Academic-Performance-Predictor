"""Loads production ML artifacts and serves predictions + SHAP explanations.

Loaded once at process startup (module-level singleton) rather than per
request — model/preprocessor loading is expensive and the artifacts are
immutable until the next training run promotes a new production model.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

from app.core.config import get_settings

FEATURE_ORDER = [
    "previous_gpa",
    "previous_semester_gpa",
    "attendance_percentage",
    "quiz_avg",
    "assignment_avg",
    "midterm_score",
    "project_score",
    "lab_score",
    "completed_courses",
    "credit_load",
    "historical_trend",
]


class ModelRegistry:
    def __init__(self, registry_dir: Path):
        self.registry_dir = registry_dir
        production = json.loads((registry_dir / "production.json").read_text())

        self.preprocessor = joblib.load(registry_dir / "preprocessor.joblib")
        self.label_encoder = joblib.load(registry_dir / "label_encoder.joblib")
        self.classification_model = joblib.load(registry_dir / production["classification_model_file"])
        self.regression_model = joblib.load(registry_dir / production["regression_model_file"])
        self.class_labels: list[str] = production["class_labels"]
        self.classification_model_name = production["classification_model_file"].removeprefix(
            "classification_"
        ).removesuffix(".joblib")
        self.regression_model_name = production["regression_model_file"].removeprefix(
            "regression_"
        ).removesuffix(".joblib")

        # SHAP explainers. KernelExplainer would work for any model but is
        # slow; since our production candidates are linear/tree-based we use
        # the appropriate fast explainer for each.
        self._classification_explainer = self._build_explainer(self.classification_model)
        self._regression_explainer = self._build_explainer(self.regression_model)

    @staticmethod
    def _build_explainer(model):
        model_type = type(model).__name__
        if model_type in ("RandomForestClassifier", "RandomForestRegressor", "XGBClassifier", "XGBRegressor", "DecisionTreeClassifier"):
            return shap.TreeExplainer(model)
        # Linear models (LogisticRegression, LinearRegression) and SVC fall
        # back to a small-background KernelExplainer/LinearExplainer path.
        if model_type in ("LogisticRegression", "LinearRegression"):
            return shap.LinearExplainer(model, np.zeros((1, len(FEATURE_ORDER))))
        return None  # e.g. SVC — explanation gracefully omitted, never fabricated

    def to_feature_frame(self, feature_dict: dict) -> pd.DataFrame:
        return pd.DataFrame([[feature_dict[f] for f in FEATURE_ORDER]], columns=FEATURE_ORDER)


@lru_cache
def get_registry() -> ModelRegistry:
    settings = get_settings()
    registry_dir = Path(settings.MODEL_REGISTRY_DIR)
    if not registry_dir.is_absolute():
        # MODEL_REGISTRY_DIR is relative to backend/ in .env; resolve from this file's location.
        registry_dir = (Path(__file__).resolve().parents[2] / settings.MODEL_REGISTRY_DIR).resolve()
    return ModelRegistry(registry_dir)


def risk_level_from_category(category: str) -> str:
    return {"At Risk": "HIGH", "Average": "MEDIUM", "Good": "LOW", "Excellent": "LOW"}[category]


def predict_for_student(feature_dict: dict) -> dict:
    """Returns classification + regression predictions with SHAP-based
    explanations. Never claims certainty — confidence is the model's own
    predicted-class probability, presented as an estimate."""
    registry = get_registry()
    X_raw = registry.to_feature_frame(feature_dict)
    X_transformed = registry.preprocessor.transform(X_raw)

    # --- Classification (Task A) ---
    class_proba = registry.classification_model.predict_proba(X_transformed)[0]
    class_idx = int(np.argmax(class_proba))
    predicted_category = registry.class_labels[class_idx]
    confidence = float(class_proba[class_idx])
    risk_level = risk_level_from_category(predicted_category)

    classification_explanation = _explain(
        registry._classification_explainer, X_transformed, class_idx, multiclass=True
    )

    # --- Regression (Task B) ---
    predicted_gpa = float(registry.regression_model.predict(X_transformed)[0])
    predicted_gpa = round(min(max(predicted_gpa, 0.0), 4.0), 3)

    regression_explanation = _explain(registry._regression_explainer, X_transformed, None, multiclass=False)

    return {
        "classification": {
            "predicted_category": predicted_category,
            "risk_level": risk_level,
            "confidence": round(confidence, 3),
            "model_version": registry.classification_model_name,
            "explanation": classification_explanation,
        },
        "regression": {
            "predicted_gpa": predicted_gpa,
            "model_version": registry.regression_model_name,
            "explanation": regression_explanation,
        },
    }


def _explain(explainer, X_transformed, class_idx: int | None, multiclass: bool) -> list[dict]:
    if explainer is None:
        return []  # model type has no fast explainer available — omitted, not fabricated

    raw = explainer.shap_values(X_transformed)

    if multiclass and isinstance(raw, list):
        values = raw[class_idx][0]
    elif multiclass and isinstance(raw, np.ndarray) and raw.ndim == 3:
        values = raw[0, :, class_idx]
    else:
        values = raw[0] if isinstance(raw, np.ndarray) else raw

    contributions = []
    for feature_name, value in zip(FEATURE_ORDER, values, strict=True):
        contributions.append(
            {
                "feature": feature_name,
                "contribution": round(float(value), 4),
                "direction": "positive" if value >= 0 else "negative",
            }
        )
    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    return contributions
