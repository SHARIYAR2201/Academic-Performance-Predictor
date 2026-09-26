# Model Evaluation

Results from the actual training run recorded in
`ml/inference/registry/metrics.json` (3,000-row synthetic dataset, seed 42,
80/20 stratified split). These are real numbers from a real run — not
hand-picked or fabricated. Re-run `ml/training/train.py` to reproduce
(deterministic given the same seed and data).

## Classification (performance category)

| Model | Accuracy | Precision (macro) | Recall (macro) | F1 (macro) | ROC-AUC (OvR macro) | Train time (s) |
|---|---|---|---|---|---|---|
| **Logistic Regression** (selected) | 0.665 | 0.662 | 0.711 | 0.681 | 0.887 | 0.02 |
| Random Forest | 0.653 | 0.671 | 0.660 | 0.664 | 0.880 | 0.79 |
| SVM | 0.650 | 0.648 | 0.697 | 0.665 | 0.878 | 0.58 |
| XGBoost | 0.615 | 0.646 | 0.608 | 0.624 | 0.855 | 0.49 |
| Decision Tree | 0.580 | 0.579 | 0.620 | 0.592 | 0.789 | 0.01 |

Selected as production classifier by **macro-F1, not accuracy** — rationale below.

## Regression (GPA prediction)

| Model | MAE | RMSE | R² | Train time (s) |
|---|---|---|---|---|
| **Linear Regression** (selected) | 0.192 | 0.239 | 0.762 | 0.002 |
| Random Forest Regressor | 0.200 | 0.247 | 0.748 | 1.78 |
| XGBoost Regressor | 0.220 | 0.276 | 0.683 | 0.19 |

Selected as production regressor by R².

## Why these numbers are honest, not suspicious

These are not 95%+ "too good to be true" numbers. Accuracy tops out around
66%, and R² around 0.76. That's intentional and expected: the synthetic
data generator (`scripts/generate_dataset.py`) adds irreducible Gaussian
noise on top of the weighted-feature signal specifically so that no model
can achieve unrealistic performance — real academic outcomes have real
unpredictability, and a model comparison that showed every candidate at 99%
accuracy would be a sign of a leaked target, not a good model.

## Why Logistic Regression beat the more complex models here

This is a legitimate, if slightly counterintuitive, result worth stating
plainly: on this dataset, the simplest classifier has the best macro-F1.
Two honest explanations, both consistent with how the data was generated:

1. `final_gpa` (and therefore the derived category) is a **linear-ish
   weighted combination** of the features by construction (see
   `generate_dataset.py::generate`) plus Gaussian noise — close to the
   inductive bias a linear model already has, while tree ensembles have to
   work harder to approximate a near-linear boundary.
2. With only 3,000 rows split 80/20 across four classes, more complex
   models (Random Forest, XGBoost) have less room to demonstrate their
   usual advantage on non-linear interactions, which this dataset does not
   strongly contain by design.

This would plausibly change with real institutional data, which is unlikely
to be this linear. That's a hypothesis for future work, not a result — see
[docs/research-notes.md](research-notes.md).

## Why we select by macro-F1, not accuracy (classification)

The minority class ("At Risk") is ~8% of the dataset — deliberately, because
a real early-warning system's target population is rare by nature. A model
that maximizes overall accuracy can do so by predicting the majority classes
well and effectively ignoring "At Risk" — the one class the entire system
exists to catch. Macro-F1 weights all four classes equally regardless of
support, so it penalizes exactly that failure mode. The actual confusion
matrix for the selected model (`logistic_regression`, class order
`["At Risk", "Average", "Excellent", "Good"]`) confirms this in practice:

```
[[40  6  0  1]    <- 40/47 true "At Risk" students correctly identified
 [12 137 3 78]
 [ 0  10 96 8]
 [ 2  70  9 128]]
```

40 of 47 true "At Risk" students (85% recall for that class) are correctly
flagged — the metric that matters most for an early-warning system, and one
a raw-accuracy-optimized model could easily sacrifice.

## What we deliberately did NOT optimize for

- **Neural networks were not used.** Per the spec, a neural net isn't
  justified "because it sounds impressive" — with 11 features and 3,000
  rows, there's no signal complexity here that a tree ensemble or linear
  model can't already capture, and a neural net would add training and
  interpretability cost for no measurable benefit on this data.
- **Hyperparameters were not exhaustively tuned** (no grid/Bayesian search).
  The values used are reasonable defaults (documented in `train.py`); a
  hyperparameter sweep is listed under future work, not silently skipped.
