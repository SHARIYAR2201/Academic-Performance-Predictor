# Project Description

## Intelligent Academic Performance Prediction & Early-Warning System

A full-stack academic analytics platform that predicts student performance
and flags at-risk students early, using real machine learning models
trained on data, served through a role-based REST API, with an
explainable-AI layer (SHAP) so every prediction shows *why* the model
reached its conclusion.

This file is a project-level overview and status record — what the system
actually does, what's been verified working (including on this machine,
Windows), and how to run it. See `README.md` for the original build
documentation and `docs/` for architecture, database, ML, security, and
deployment detail.

---

## What this system does

1. **Four roles** — student, instructor, admin, super_admin — each with
   access strictly scoped by the backend's service layer, not just the UI.
   An instructor can only enter grades for courses they're actually
   assigned to teach; a student can only view their own data; an admin
   can manage everything.
2. **Two real ML tasks** predicted from a student's actual academic
   record (GPA history, attendance, quiz/assignment/midterm/project/lab
   scores):
   - **Classification**: performance category (`Excellent` / `Good` /
     `Average` / `At Risk`)
   - **Regression**: a continuous predicted GPA (0.0–4.0)
3. **Explainable AI** — every prediction ships with a SHAP-based
   breakdown of which features pushed it up or down, rendered as a chart
   in the student dashboard.
4. **Early-warning system** — LOW / MEDIUM / HIGH risk levels, with an
   instructor-facing roster view.
5. **Full audit trail** — every prediction and its explanation is
   persisted to the database, not just computed and thrown away.

**Every prediction is a model-generated estimate, not a certainty**, and
the API/UI both say so explicitly (`PredictionResponse.disclaimer`).

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), TypeScript, React, Tailwind CSS, Recharts |
| Backend | Python, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| ML | NumPy, Pandas, scikit-learn, XGBoost, SHAP, joblib |
| Database | PostgreSQL 16 |
| Infra | Docker, Docker Compose, GitHub Actions |

---

## Verified status

This is not a claim — it's what has actually been run and observed to
pass, both during the original build and on this machine:

- ✅ **25/25 automated tests pass** (`pytest tests/ -v`) — 12 backend
  integration tests (auth, RBAC scoping, prediction access control) + 13
  ML tests (preprocessing, no-data-leakage, real model inference).
- ✅ **Full auth flow verified live**: register → login → JWT access/
  refresh tokens → `/auth/me`.
- ✅ **RBAC verified live**: an instructor assigned to Course A can grade
  it (201) but is rejected from Course B (403); a student cannot write
  any academic record (403); a student cannot view another student's
  prediction (403).
- ✅ **Real ML training run**: 5 classifiers + 3 regressors trained and
  compared on a 3,000-row synthetic dataset. Production models selected
  by macro-F1 (classification) and R² (regression) — not raw accuracy —
  with the rationale documented in `docs/model-evaluation.md`. Real
  numbers: Logistic Regression f1_macro = 0.681, Linear Regression
  R² = 0.762.
- ✅ **Full prediction pipeline verified live on this machine**: seeded a
  real department/course/instructor/student through the actual API,
  recorded real grades and attendance, generated a real prediction —
  `predicted_category: "Average"`, `risk_level: "MEDIUM"`,
  `confidence: 0.798`, `predicted_gpa: 2.704`, with a full SHAP
  explanation — persisted to the `predictions` /
  `prediction_explanations` tables.
- ✅ **Frontend builds and serves cleanly**, all three dashboards
  (student/instructor/admin) confirmed calling the real backend API and
  rendering real data, including the SHAP explanation chart.
- ⚠️ **Docker / docker-compose**: written carefully but **not run-verified**
  — no Docker daemon was available in the environment this was built in.
  Treat `docker-compose.yml` and the two Dockerfiles as unverified until
  you run `docker compose up --build` yourself.
- ⚠️ **No dataset-upload endpoint or admin "promote model" UI** yet — model
  registration into the database currently happens via
  `ml/training/register_models.py`, not an admin dashboard action.
- ⚠️ **No frontend automated test suite** (Jest/RTL) — only
  `npm run build`'s type-check is currently wired into CI.

---

## Running it (Windows-specific notes from actually doing it)

The steps below are the exact sequence that worked on a real Windows
machine, including the gotchas that came up and their fixes. If you're on
macOS/Linux, the general flow is the same but simpler — see `README.md`.

### 1. PowerShell execution policy

Windows blocks running `.ps1` scripts (including `venv`'s own activation
script and even `npm`, which is itself a `.ps1` on Windows) by default.
Fix once per machine:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### 2. Backend setup
```powershell
cd backend
py -3.12 -m venv .venv          # must be Python 3.12 — numpy/scikit-learn/xgboost pin to it
.venv\Scripts\Activate.ps1
```

**`requirements.txt` was generated on Linux** and contains packages that
don't exist for Windows: `nvidia-*` / `triton` (CUDA-only, pulled in by
xgboost's Linux wheel) and `uvloop` (Linux/macOS-only event loop). Strip
them before installing:
```powershell
(Get-Content requirements.txt) | Where-Object { $_ -notmatch '^nvidia-' -and $_ -notmatch '^triton' -and $_ -notmatch '^uvloop' } | Set-Content requirements.txt
python -m pip install -r requirements.txt
```

### 3. Database
Postgres must actually be installed and running, with a database created
and the `citext` extension enabled — none of this happens automatically:
```powershell
$env:PGPASSWORD = "your_actual_postgres_password"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE academic_predictor;"
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost -d academic_predictor -c "CREATE EXTENSION IF NOT EXISTS citext;"
```
(adjust the `16` in the path to whatever version `Get-ChildItem "C:\Program Files\PostgreSQL" -Recurse -Filter "psql.exe"` finds)

Then update `backend\.env`'s `DATABASE_URL` with the real password:
```
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_REAL_PASSWORD@localhost:5432/academic_predictor
```

### 4. Migrate + start backend
```powershell
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```
Verify at `http://127.0.0.1:8000/health` and `http://127.0.0.1:8000/docs`.

### 5. Frontend (separate terminal)
```powershell
cd frontend
npm install
npm run dev
```
Verify at `http://localhost:3000` (redirects to `/login`).

### 6. Seed demo data + see a real prediction
`backend/seed_demo.ps1` creates a department, course, semester,
instructor, student, real grades/attendance, and generates an actual
prediction through the live API — run it from a **third** terminal (keep
uvicorn and `npm run dev` running in the other two):
```powershell
cd backend
.venv\Scripts\Activate.ps1
.\seed_demo.ps1
```
It prints login credentials and IDs to use in the frontend at the end.

---

## Known demo accounts (from `seed_demo.ps1`)

| Role | Email | Password |
|---|---|---|
| Admin | admin@demo.edu | password123 |
| Instructor | instructor@demo.edu | password123 |
| Student | student@demo.edu | password123 |

These are local development credentials only — never use anything like
this in a real deployment.

---

## Project structure

```
academic-performance-predictor/
├── backend/          FastAPI app, SQLAlchemy models, Alembic migrations, tests
├── frontend/          Next.js dashboards (student / instructor / admin)
├── ml/                Preprocessing pipeline, training script, inference registry
├── data/synthetic/    Generated synthetic training data (clearly not real data)
├── docs/              Architecture, database, ML, security, deployment, research notes
├── docker/            Postgres init script (citext extension)
├── .github/workflows/ CI pipeline (lint, test, train, build)
├── docker-compose.yml
└── README.md          Full build documentation
```

---

## Limitations (stated plainly, not hidden)

- The training dataset is **entirely synthetic** — every relationship
  (attendance → performance, GPA history → outcome) is hand-specified
  with documented noise, not real institutional data. Model metrics
  describe performance on this synthetic data only.
- JWT logout is stateless (no server-side token blacklist yet).
- Docker/CI have not been run end-to-end in any environment yet — you are
  the first real test of them.

See `README.md`'s Limitations section and `docs/research-notes.md` for
the full, honest accounting.
