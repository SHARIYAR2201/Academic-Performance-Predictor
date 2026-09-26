"""Reusable preprocessing pipeline.

Critical invariant (spec section 11): the exact same fitted pipeline object
used at training time must be used at inference time. We enforce this by
persisting the fitted ColumnTransformer alongside the model (see
ml/training/train.py and ml/inference/predict.py) rather than re-deriving
preprocessing logic in two places.
"""
from __future__ import annotations

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

NUMERIC_FEATURES = [
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
]
CATEGORICAL_FEATURES: list[str] = []  # historical_trend is already numeric-encoded (-1/0/1)
ALL_FEATURES = NUMERIC_FEATURES + ["historical_trend"]

CLASSIFICATION_TARGET = "performance_category"
REGRESSION_TARGET = "final_gpa"


def build_preprocessing_pipeline() -> ColumnTransformer:
    """Median-impute missing numeric values (spec: missing-value handling),
    then standard-scale. historical_trend is a small ordinal (-1/0/1) and is
    passed through unscaled so it keeps its interpretable meaning for SHAP.
    """
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    return ColumnTransformer(
        transformers=[("numeric", numeric_pipeline, NUMERIC_FEATURES)],
        remainder="passthrough",  # passes historical_trend through as-is
        verbose_feature_names_out=False,
    )


def validate_dataset(df: pd.DataFrame) -> list[str]:
    """Returns a list of validation error strings; empty list means valid.
    Spec section 20: validate required columns, detect missing/invalid values.
    """
    errors: list[str] = []
    required = set(ALL_FEATURES) | {REGRESSION_TARGET}
    missing_cols = required - set(df.columns)
    if missing_cols:
        errors.append(f"Missing required columns: {sorted(missing_cols)}")
        return errors  # can't validate further without the columns

    if df[REGRESSION_TARGET].isna().any():
        errors.append("final_gpa contains missing values; rows with missing target must be dropped before training.")
    if not df[REGRESSION_TARGET].between(0, 4.0).all():
        errors.append("final_gpa contains values outside the valid 0.0-4.0 range.")
    if "attendance_percentage" in df and not df["attendance_percentage"].between(0, 100).all():
        errors.append("attendance_percentage contains values outside the valid 0-100 range.")

    return errors


def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Duplicate detection + basic outlier flagging (spec section 11).
    Returns (cleaned_df, report) — never silently drops outliers, only flags
    them, since extreme-but-real academic outcomes are legitimate signal.
    """
    report: dict = {}
    before = len(df)
    df = df.drop_duplicates()
    report["duplicates_removed"] = before - len(df)

    # Outlier flag via IQR on the regression target, for reporting only.
    q1, q3 = df[REGRESSION_TARGET].quantile([0.25, 0.75])
    iqr = q3 - q1
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    report["target_outliers_flagged"] = int(((df[REGRESSION_TARGET] < lower) | (df[REGRESSION_TARGET] > upper)).sum())

    return df.reset_index(drop=True), report
