# Intelligent Academic Performance Prediction & Early-Warning System

A full-stack academic analytics platform that predicts student performance and
flags at-risk students early, using real machine learning models trained on
data, served through a role-based REST API, with an explainable-AI layer
(SHAP) so every prediction shows *why* the model reached its conclusion.

**This is not a toy CRUD app with a bolted-on model.** It's a complete
system: normalized PostgreSQL schema, JWT auth with four enforced roles,
5 classifiers + 3 regressors trained and compared on their actual metrics,
a real prediction pipeline (DB → features → model → SHAP → persisted result),
role-aware dashboards, an automated test suite, Docker, and CI.

> ⚠️ **All predictions are model-generated estimates**, not certainties, and
> must never be the sole basis for grading, disciplinary, or admissions
> decisions. The development dataset is **entirely synthetic** — see
> [Limitations](#limitations--honest-status).

## Problem statement

Universities generate large amounts of academic data (grades, attendance,
assessments) but rarely turn it into an early-warning signal instructors and
students can actually act on before a semester is lost. This system closes
that loop: it aggregates a student's real academic records into a feature
vector, runs it through a trained model, and surfaces a plain-language,
explained risk estimate to the student, their instructor, and administrators
— with access strictly scoped by role.

## Features

- **Four roles** (student, instructor, admin, super_admin) with RBAC enforced
  at the service layer, not just route decorators — verified with automated
  tests (an instructor can grade *their own* course but is rejected with a
  403 from a course they don't teach; a student cannot write any academic
  record; a student cannot view another student's prediction).
- **Two real ML tasks**: performance-category classification (Excellent /
  Good / Average / At Risk) and GPA regression, each with 5 and 3 candidate
  models respectively, compared on real held-out metrics (not just accuracy
  — see [Model evaluation](docs/model-evaluation.md) for why).
- **Explainable AI**: every prediction ships with a SHAP-based, per-feature
  contribution breakdown, rendered as a chart in the student dashboard.
- **Early-warning system**: LOW / MEDIUM / HIGH risk levels, with an
  instructor-facing roster view flagging at-risk students.
- **Full audit trail**: every prediction and its explanation is persisted;
  `audit_logs` table is in place for administrative actions.
- **Dockerized**, with CI running lint + the full test suite + a model
  training run + a Docker build validation on every push.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), TypeScript, React, Tailwind CSS, Recharts |
| Backend | Python, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| ML | NumPy, Pandas, scikit-learn, XGBoost, SHAP, joblib |
| Database | PostgreSQL 16 |
| Infra | Docker, Docker Compose, GitHub Actions |

See [docs/architecture.md](docs/architecture.md) for the full system diagram
and request flows, and [docs/database.md](docs/database.md) for the schema.

## Screenshots

Not included in this repository snapshot — the frontend is best explored by
running it locally (see below); the student dashboard's prediction +
explanation view and the instructor roster view are the two most relevant
screens to look at first.

## Live ML demo (Streamlit)

A standalone Streamlit demo lives at the repository root (`streamlit_app.py`). It is
a **read-only demonstration of the machine-learning layer**, not a replacement for
the full application:

- Loads the trained artifacts from `ml/inference/registry/` directly
- Reuses the backend's real preprocessing, inference, risk mapping, and SHAP logic
- Shows predicted category, LOW/MEDIUM/HIGH risk, predicted GPA, and SHAP contributions
- Includes model-comparison metrics and a synthetic-dataset explorer
- **No PostgreSQL, FastAPI, auth, RBAC, or persisted predictions**

The Next.js + FastAPI + PostgreSQL application remains the full system. The Streamlit
app is intended for [Streamlit Community Cloud](https://share.streamlit.io) and is
deployed from the repository root with `streamlit_app.py` as the entrypoint.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Use Python 3.12 if possible. The root `requirements.txt` is for the Streamlit demo
only; the backend keeps its own dependencies in `backend/requirements.txt`.

## Installation

### Prerequisites
- Docker + Docker Compose (recommended path), **or**
- Python 3.12, Node 22, and a local PostgreSQL 16 instance

### Option A — Docker Compose

```bash
cp .env.example .env      # edit SECRET_KEY etc. for anything beyond local dev
docker compose up --build
```

This starts Postgres, runs Alembic migrations automatically (see
`backend/docker-entrypoint.sh`), and starts the backend on `:8000` and
frontend on `:3000`. **You still need to generate a model registry before
predictions will work** — see [ML training](#ml-training) below; the
`ml/inference/registry/` directory is mounted read-only into the backend
container.

> **Honesty note:** the Docker setup in this repository has been written
> carefully and validated piece-by-piece (the Next.js standalone build output,
> the entrypoint's DB-readiness/migration logic, Alembic idempotency) but
> **`docker compose up` itself has not been run end-to-end**, because no
> Docker daemon was available in the environment this was built in. Please
> treat it as unverified until you run it once yourself, and file/fix
> anything that doesn't work — the individual pieces are real, but the
> full integration hasn't been observed running together.

### Option B — Run natively

```bash
# 1. Database
createdb academic_predictor
psql -d academic_predictor -c "CREATE EXTENSION IF NOT EXISTS citext;"

# 2. Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # adjust DATABASE_URL if needed
alembic upgrade head
uvicorn app.main:app --reload   # http://localhost:8000/docs

# 3. ML (generate data + train + register — see below)

# 4. Frontend
cd ../frontend
npm install
npm run dev   # http://localhost:3000
```

### Option C — Streamlit ML demo

If you only want the public prediction demo (no database, backend, or Next.js):

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py   # http://localhost:8501
```

This path is documented in
[docs/deployment.md](docs/deployment.md#streamlit-community-cloud-standalone-ml-demo).

## Environment setup

See [.env.example](.env.example) at the repo root for every variable, with
comments. Never commit a real `.env`.

## Database setup

Schema is fully defined via SQLAlchemy models (`backend/app/models/`) and
managed by Alembic (`backend/alembic/versions/`). See
[docs/database.md](docs/database.md) for the full DDL and design rationale
(generated columns, partial unique indexes, naming conventions).

```bash
cd backend
alembic upgrade head      # apply
alembic downgrade base    # roll back everything (verified reversible)
```

## ML training

```bash
# From the repo root, using either venv (ml/.venv or backend/.venv both work)
python scripts/generate_dataset.py --n 3000 --seed 42 \
    --out data/synthetic/students_synthetic_v1.csv

python ml/training/train.py \
    --data data/synthetic/students_synthetic_v1.csv \
    --registry ml/inference/registry \
    --dataset-version 1.0

# Optional: register the trained models + dataset into Postgres (ml_models table)
python ml/training/register_models.py \
    --db-url postgresql://postgres:postgres@localhost:5432/academic_predictor
```

This trains and evaluates all 8 models (see
[docs/model-evaluation.md](docs/model-evaluation.md) for the real numbers)
and writes `preprocessor.joblib`, `label_encoder.joblib`, one `.joblib` per
model, `metrics.json`, and `production.json` to the registry directory. The
FastAPI backend loads this registry lazily on first prediction request.

## API documentation

Interactive Swagger UI at `http://localhost:8000/docs` once the backend is
running (auto-generated by FastAPI from the Pydantic schemas). See also
[docs/api.md](docs/api.md) for a narrative walkthrough of the auth flow and
the prediction endpoint's RBAC rules.

## Testing

```bash
cd backend
pytest tests/ -v
```

**25/25 tests passing** as of this snapshot: 12 backend integration tests
(auth, RBAC scoping — including the specific instructor-can-only-grade-
their-own-course case, prediction endpoint access control) and 13 ML tests
(preprocessing validation/cleaning, no-data-leakage invariant, real model
loading, prediction shape, and a directional sanity check that stronger
inputs produce a higher predicted GPA). These run against a real Postgres
instance and the real trained model artifacts — not mocks.

Frontend: `npm run build` type-checks and builds the whole app (this is the
test currently wired into CI); a Jest/RTL component test suite is not yet
set up — documented as a known gap, see
[Limitations](#limitations--honest-status).

## Deployment

See [docs/deployment.md](docs/deployment.md). The Streamlit ML demo can be deployed
for free on Streamlit Community Cloud; the full FastAPI + PostgreSQL + Next.js
application still needs separate backend/database hosting.

## Limitations & honest status

This section exists because the project brief explicitly asks for it, and
because a portfolio project is more credible when it says what *isn't* done
rather than implying everything is:

- **The synthetic dataset is not real data.** Class balance, feature
  correlations, and noise levels are hand-designed to be plausible, not
  fitted to any real institution. All ML results in this repo (see
  `ml/inference/registry/metrics.json`) describe how these models perform
  on *this synthetic data* — not a claim about real-world predictive power.
- **Docker Compose is written but not run-verified** (see the note under
  Installation above) — no Docker daemon was available to test it.
- **Frontend has no automated test suite yet** (build/type-check only).
  A Jest + React Testing Library setup for the dashboard components is the
  natural next step.
- **JWT logout is stateless** — tokens aren't blacklisted server-side, so a
  stolen access token remains valid until it expires (max 30 minutes by
  default). A production deployment should add a Redis-backed token
  blacklist; the `redis` service is anticipated in the architecture but not
  wired in yet.
- **Model promotion is file-based** (`ml/inference/registry/production.json`)
  rather than driven by an admin UI action against the `ml_models.is_production`
  column, though the DB-level constraint (partial unique index — only one
  production model per task) and the `register_models.py` script both work;
  wiring a "promote" button in the admin dashboard is the natural next step.
- **CI's Docker build-validation job has not been observed running** for the
  same reason as above — the YAML is correct per GitHub Actions' documented
  behavior, but wasn't dry-run in this environment.

## Future work

- Redis-backed JWT blacklist for real logout semantics.
- Admin UI for dataset upload + model promotion (backend endpoints exist for
  most of this already — `POST /api/datasets`, `ml_models` table — the
  remaining piece is mostly frontend).
- MLflow experiment tracking, as an upgrade over the current flat
  `metrics.json` + `production.json` file-based registry.
- Class-imbalance techniques beyond `sample_weight` (e.g. SMOTE) — worth
  comparing against the current approach once real (non-synthetic) data
  is available, since synthetic imbalance may not reflect a real cohort's.
- Jest/RTL frontend test suite.
- A genuine end-to-end Docker Compose verification run.

## License

MIT — see [LICENSE](LICENSE).
