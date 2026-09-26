# Machine Learning Approach

## The two prediction tasks

1. **Classification** — performance category: `Excellent` / `Good` /
   `Average` / `At Risk`, derived from `final_gpa` via documented thresholds
   (see `scripts/generate_dataset.py::classify`). These thresholds are a
   configurable, documented convention for this project, **not a claim of
   objective academic truth**.
2. **Regression** — predicted GPA (0.0–4.0 continuous).

## Features used (and why)

| Feature | Rationale |
|---|---|
| `previous_gpa` | Strongest single predictor of future academic performance in general. |
| `previous_semester_gpa` | Captures recent trajectory, not just lifetime average. |
| `attendance_percentage` | Well-established correlate of academic outcomes. |
| `quiz_avg`, `assignment_avg`, `midterm_score`, `project_score`, `lab_score` | Direct current-semester signal, one per assessment type. |
| `completed_courses` | Proxy for class standing/experience. |
| `credit_load` | Captures workload pressure. |
| `historical_trend` | Ordinal (-1/0/1): whether the student's GPA is declining, stable, or improving over the last two semesters. |

No demographic or otherwise non-academic attribute is used anywhere in the
feature set (spec requirement — see `ml/preprocessing/pipeline.py`).

## Preprocessing pipeline

`ml/preprocessing/pipeline.py` builds a single `sklearn.ColumnTransformer`:
median-imputation for missing numeric values, then standard scaling. It is
**fit once, on the training split only**, and the exact fitted object is
persisted (`preprocessor.joblib`) and reused, unmodified, at inference time
— this is the mechanism that prevents train/inference skew and data leakage.
Verified by an automated test
(`tests/ml/test_preprocessing.py::test_same_fitted_pipeline_used_for_new_data_no_leakage`).

`historical_trend` is passed through unscaled (it's already a small ordinal
in {-1, 0, 1}) so its SHAP contribution stays directly interpretable.

## Training pipeline (`ml/training/train.py`)

Follows: load → validate → clean (de-dup + outlier flagging) → stratified
80/20 split → fit preprocessing on train only → train all candidate models
→ evaluate on the held-out test split → compare → save metrics + artifacts
→ (optionally) register into Postgres via `register_models.py`.

**Class imbalance**: the synthetic dataset's minority class ("At Risk") is
~8% of rows — deliberately, since a real early-warning system's target
population is a minority by definition. Every classifier is trained with
`sample_weight = compute_sample_weight("balanced", y_train)` so the minority
class isn't simply ignored in favor of overall accuracy.

## Model selection — and why it isn't "pick the highest accuracy"

See [docs/model-evaluation.md](model-evaluation.md) for the full numbers and
the documented rationale (`select_classification_production` /
`select_regression_production` in `ml/training/train.py`): classification is
selected by **macro-F1**, not accuracy, because accuracy can be maximized by
a model that never predicts "At Risk" at all — exactly the failure mode an
early-warning system cannot afford. Regression is selected by **R²**.

## Explainability (SHAP)

`app/services/inference_service.py` builds a `shap.TreeExplainer` for
tree-based models and a `shap.LinearExplainer` for linear models (falls back
to omitting the explanation, never fabricating one, for model types with no
fast explainer wired up — e.g. SVM). Contributions are returned sorted by
absolute magnitude and rendered as a bar chart in the student dashboard
(green = pushed the prediction up, red = pushed it down).

**SHAP values describe the trained model's own behavior for one specific
prediction. They are not proof of real-world cause and effect** — this
disclaimer is both in the API response (`PredictionResponse.disclaimer`)
and directly under the chart in the UI.

## Known limitation

The dataset is synthetic (see `scripts/generate_dataset.py` — every relationship
is hand-specified with documented noise, not fit to real institutional data).
All metrics in this document are true *of this synthetic data*, not a claim
about real-world predictive performance. See the README's
[Limitations](../README.md#limitations--honest-status) section.
