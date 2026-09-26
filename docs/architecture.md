# Architecture — Intelligent Academic Performance Prediction & Early-Warning System

## 1. System Overview

A modular, three-tier web application with a separate ML training/inference subsystem.

```
                        ┌─────────────────────┐
                        │   Next.js Frontend   │
                        │  (React + TS + shadcn)│
                        └──────────┬───────────┘
                                   │ HTTPS / REST (JSON)
                                   ▼
                        ┌─────────────────────┐
                        │     Nginx (proxy)    │
                        └──────────┬───────────┘
                                   ▼
                        ┌─────────────────────┐
                        │   FastAPI Backend    │
                        │  ┌─────────────────┐ │
                        │  │ Auth / RBAC      │ │
                        │  │ Academic Service │ │
                        │  │ Dataset Service  │ │
                        │  │ Prediction Svc   │ │
                        │  │ Analytics Svc    │ │
                        │  │ Audit Service    │ │
                        │  └─────────────────┘ │
                        └──────┬─────────┬──────┘
                               │         │
                 SQLAlchemy/   │         │  Loads model artifacts
                 Alembic       ▼         ▼  (joblib / SHAP explainer)
                        ┌───────────┐  ┌────────────────┐
                        │ PostgreSQL│  │  ml/inference/   │
                        │           │  │  model registry  │
                        └───────────┘  └────────┬─────────┘
                                                 │
                                        ┌────────▼─────────┐
                                        │   ml/training/    │
                                        │  offline pipeline │
                                        │ (run via CLI/API) │
                                        └────────────────────┘
```

## 2. Request Flow — Prediction

```
Frontend → POST /api/predictions {student_id}
  → FastAPI validates JWT + role (student=self, instructor=assigned, admin=any)
  → Prediction Service loads latest academic features for student from Postgres
  → Feature vector passed through persisted preprocessing pipeline (joblib)
  → Production model (ml_models.is_production = true) predicts:
      - risk classification (LOW/MEDIUM/HIGH or Excellent/Good/Average/At Risk)
      - GPA regression estimate
  → SHAP explainer computes per-feature contributions
  → Prediction + explanation rows persisted (predictions, prediction_explanations)
  → Response returned to frontend with explicit "model-generated estimate" framing
```

## 3. Training Pipeline Flow

```
Dataset (CSV upload or synthetic generator)
  → Validation (schema, types, required columns)
  → Cleaning (missing values, duplicates, outlier flags)
  → Feature Engineering (rolling GPA, attendance %, assessment averages)
  → Train/Test Split (stratified for classification)
  → Preprocessing Pipeline (sklearn ColumnTransformer: scaling + encoding)
  → Train N models (classification + regression) in parallel configs
  → Evaluate (accuracy/F1/ROC-AUC or MAE/RMSE/R², + timing)
  → Compare + select candidate (documented rationale, not just top accuracy)
  → Persist: model.joblib, preprocessor.joblib, metrics.json, SHAP explainer
  → Register in ml_models table (version, metrics, training_dataset_id)
  → Admin optionally promotes to production (is_production=true, only one active per task)
```

## 4. Module Boundaries

| Layer | Responsibility | Never does |
|---|---|---|
| Frontend | Presentation, client-side validation, role-aware routing | Direct DB access, business rules |
| FastAPI routers | Request/response shape, auth guard | Business logic |
| Services (application layer) | Business rules, authorization scoping | SQL specifics (delegates to repositories) |
| SQLAlchemy models/repositories | Persistence | Business rules |
| ml/training | Offline model building | Serve live traffic |
| ml/inference | Load artifact, predict, explain | Retrain |

## 5. Authorization Model (RBAC scoping)

- **student**: row-level scope — only `students.user_id == current_user.id`
- **instructor**: scope via `instructor_id` on `courses`/`enrollments` — only assigned courses/students
- **admin**: scope via institution-wide read/write except super-admin-only tables
- **super_admin**: full access, including `audit_logs`, `ml_models` config, permission management

Enforced at the service layer (not just UI) via a dependency-injected `current_user` + policy check on every mutating and sensitive read endpoint.

## 6. Non-functional decisions

- **Sync vs async**: FastAPI async endpoints; SQLAlchemy 2.0 async engine for the API; training pipeline runs as a separate sync/batch process (invoked via `/api/ml/train`, executed as a background task, not blocking the request).
- **Model registry**: filesystem + Postgres metadata (MLflow optional, documented as an upgrade path, not required for local dev).
- **Secrets**: `.env` via `pydantic-settings`, never committed; `.env.example` provided.
- **Caching**: Redis reserved for rate limiting/session blacklist (JWT revocation), optional for MVP.
