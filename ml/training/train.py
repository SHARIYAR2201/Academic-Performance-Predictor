"""Training pipeline (spec section 14):
  load -> validate -> clean -> split -> preprocess -> train (multiple models)
  -> evaluate -> compare -> save metrics -> save artifacts -> register.

Trains 5 classifiers (Task A: performance category) and 3 regressors
(Task B: GPA regression), per spec section 10.

Usage:
    python ml/training/train.py --data data/synthetic/students_synthetic_v1.csv \
        --registry ml/inference/registry --dataset-version 1.0
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier, XGBRegressor

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for `ml.` imports

from ml.evaluation.metrics import classification_metrics, regression_metrics
from ml.preprocessing.pipeline import (
    ALL_FEATURES,
    CLASSIFICATION_TARGET,
    REGRESSION_TARGET,
    build_preprocessing_pipeline,
    clean_dataset,
    validate_dataset,
)

RANDOM_STATE = 42


def timed_fit(model, X, y, **fit_kwargs) -> float:
    start = time.perf_counter()
    model.fit(X, y, **fit_kwargs)
    return round(time.perf_counter() - start, 4)


def timed_predict(model, X) -> tuple[np.ndarray, float]:
    start = time.perf_counter()
    preds = model.predict(X)
    elapsed = round(time.perf_counter() - start, 4)
    return preds, elapsed


def run_classification_models(X_train, X_test, y_train, y_test, class_labels: list[str]) -> dict:
    sample_weight = compute_sample_weight("balanced", y_train)

    candidates = {
        "logistic_regression": LogisticRegression(max_iter=1000, random_state=RANDOM_STATE),
        "decision_tree": DecisionTreeClassifier(max_depth=8, random_state=RANDOM_STATE),
        "random_forest": RandomForestClassifier(n_estimators=200, max_depth=10, random_state=RANDOM_STATE),
        "xgboost": XGBClassifier(
            n_estimators=200, max_depth=5, eval_metric="mlogloss", random_state=RANDOM_STATE, verbosity=0
        ),
        "svm": SVC(probability=True, random_state=RANDOM_STATE),
    }

    results = {}
    fitted_models = {}
    for name, model in candidates.items():
        train_time = timed_fit(model, X_train, y_train, sample_weight=sample_weight)
        preds, infer_time = timed_predict(model, X_test)
        proba = model.predict_proba(X_test)
        metrics = classification_metrics(y_test, preds, proba, class_labels)
        metrics["training_time_seconds"] = train_time
        metrics["inference_time_seconds_per_batch"] = infer_time
        metrics["n_features"] = X_train.shape[1]
        results[name] = metrics
        fitted_models[name] = model
        print(f"  [classification/{name}] f1_macro={metrics['f1_macro']} accuracy={metrics['accuracy']}")

    return {"results": results, "models": fitted_models}


def run_regression_models(X_train, X_test, y_train, y_test) -> dict:
    candidates = {
        "linear_regression": LinearRegression(),
        "random_forest_regressor": RandomForestRegressor(n_estimators=200, max_depth=10, random_state=RANDOM_STATE),
        "xgboost_regressor": XGBRegressor(n_estimators=200, max_depth=5, random_state=RANDOM_STATE, verbosity=0),
    }

    results = {}
    fitted_models = {}
    for name, model in candidates.items():
        train_time = timed_fit(model, X_train, y_train)
        preds, infer_time = timed_predict(model, X_test)
        metrics = regression_metrics(y_test, preds)
        metrics["training_time_seconds"] = train_time
        metrics["inference_time_seconds_per_batch"] = infer_time
        metrics["n_features"] = X_train.shape[1]
        results[name] = metrics
        fitted_models[name] = model
        print(f"  [regression/{name}] r2={metrics['r2']} mae={metrics['mae']} rmse={metrics['rmse']}")

    return {"results": results, "models": fitted_models}


def select_classification_production(results: dict) -> str:
    """Documented rationale (spec section 15): do NOT pick by raw accuracy
    alone. With ~8% minority class ("At Risk" — the class that matters most
    for an early-warning system), a model that maximizes accuracy can do so
    by neglecting that class entirely. We select by macro-F1, which weights
    all four classes equally regardless of support, so it penalizes a model
    that ignores At Risk students even if overall accuracy looks strong."""
    return max(results, key=lambda name: results[name]["f1_macro"])


def select_regression_production(results: dict) -> str:
    """Select by R² (variance explained) as the primary criterion, since MAE/RMSE
    alone don't indicate whether a model beats a naive mean-predictor baseline."""
    return max(results, key=lambda name: results[name]["r2"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--registry", type=str, default="ml/inference/registry")
    parser.add_argument("--dataset-version", type=str, default="1.0")
    args = parser.parse_args()

    print(f"1. Loading dataset: {args.data}")
    df = pd.read_csv(args.data)
    print(f"   {len(df)} rows loaded")

    print("2. Validating dataset")
    errors = validate_dataset(df)
    if errors:
        raise SystemExit(f"Dataset validation failed: {errors}")
    print("   OK")

    print("3. Cleaning dataset")
    df, clean_report = clean_dataset(df)
    print(f"   {clean_report}")

    print("4/5. Splitting + preprocessing")
    X = df[ALL_FEATURES]
    y_class_raw = df[CLASSIFICATION_TARGET]
    y_reg = df[REGRESSION_TARGET]

    label_encoder = LabelEncoder()
    y_class = label_encoder.fit_transform(y_class_raw)
    class_labels = list(label_encoder.classes_)

    X_train, X_test, y_class_train, y_class_test, y_reg_train, y_reg_test = train_test_split(
        X, y_class, y_reg, test_size=0.2, random_state=RANDOM_STATE, stratify=y_class
    )

    preprocessor = build_preprocessing_pipeline()
    X_train_t = preprocessor.fit_transform(X_train)  # fit ONLY on train — no leakage
    X_test_t = preprocessor.transform(X_test)

    print("6/7. Training + evaluating classification models")
    clf_outcome = run_classification_models(X_train_t, X_test_t, y_class_train, y_class_test, class_labels)

    print("6/7. Training + evaluating regression models")
    reg_outcome = run_regression_models(X_train_t, X_test_t, y_reg_train, y_reg_test)

    print("8. Comparing models")
    best_clf_name = select_classification_production(clf_outcome["results"])
    best_reg_name = select_regression_production(reg_outcome["results"])
    print(f"   Selected classification production candidate: {best_clf_name} (rationale: macro-F1, see docstring)")
    print(f"   Selected regression production candidate: {best_reg_name} (rationale: R^2, see docstring)")

    registry_dir = Path(args.registry)
    registry_dir.mkdir(parents=True, exist_ok=True)

    print("9. Saving metrics")
    all_metrics = {
        "dataset_version": args.dataset_version,
        "dataset_rows": len(df),
        "classification": clf_outcome["results"],
        "regression": reg_outcome["results"],
        "selected_production": {"classification": best_clf_name, "regression": best_reg_name},
    }
    (registry_dir / "metrics.json").write_text(json.dumps(all_metrics, indent=2))

    print("10. Saving model artifacts")
    joblib.dump(preprocessor, registry_dir / "preprocessor.joblib")
    joblib.dump(label_encoder, registry_dir / "label_encoder.joblib")
    for name, model in clf_outcome["models"].items():
        joblib.dump(model, registry_dir / f"classification_{name}.joblib")
    for name, model in reg_outcome["models"].items():
        joblib.dump(model, registry_dir / f"regression_{name}.joblib")

    (registry_dir / "production.json").write_text(
        json.dumps(
            {
                "classification_model_file": f"classification_{best_clf_name}.joblib",
                "regression_model_file": f"regression_{best_reg_name}.joblib",
                "feature_order": ALL_FEATURES,
                "class_labels": class_labels,
            },
            indent=2,
        )
    )

    print(f"\nDone. Artifacts written to {registry_dir}/")


if __name__ == "__main__":
    main()
