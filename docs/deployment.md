# Deployment

## Streamlit Community Cloud (standalone ML demo)

The repository includes a standalone Streamlit demo at the root:

```text
streamlit_app.py          # entrypoint
requirements.txt          # Streamlit-only dependencies
streamlit_demo/           # pages + inference adapter
ml/inference/registry/    # committed model artifacts loaded at runtime
```

It is a public, read-only demonstration of the ML layer. It does **not** use
PostgreSQL, FastAPI, JWT auth, RBAC, the Next.js frontend, or prediction
persistence. The full application still requires the backend/database setup
described below.

### Deploy

1. Push the repository to GitHub (the app reads committed artifacts from
   `ml/inference/registry/` — do not delete them or move them out of the repo).
2. Go to [share.streamlit.io](https://share.streamlit.io) and create a new app.
3. Select:
   - Repository: `SHARIYAR2201/Academic-Performance-Predictor`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - Python version: **3.12** if available (the ML artifacts were trained with
     Python 3.12 / scikit-learn 1.9.1)
4. Deploy. No secrets or environment variables are required.
5. Optionally add the generated URL to the README.

Streamlit Cloud installs the root `requirements.txt`, which pins the ML
package versions to the ones used to train the committed joblib artifacts.

### Local verification

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Troubleshooting

- **Model artifact cannot be unpickled / missing attribute:** the installed
  `scikit-learn` versions must match the training environment. Keep the pins in
  the root `requirements.txt` aligned with `backend/requirements.txt`.
- **`No module named 'app'`:** the demo adds `backend/` to `sys.path` from
  `streamlit_demo/model.py`; make sure the app runs from the repository root.
- **Streamlit Cloud build fails on a pinned wheel:** select Python 3.12 in the
  app's advanced settings, or adjust only the non-artifact-critical pins.
- **Model registry missing:** confirm `ml/inference/registry/production.json`
  and its referenced `.joblib` files are present in the deployed commit.

### What this deployment does not provide

- Authentication, roles, or student-record access control
- Database-backed student/instructor/admin dashboards
- Saved prediction history or audit logs
- The FastAPI API or Swagger UI

Those remain part of the full application described below.

## Local (Docker Compose) — see README


The intended local/demo deployment path. **Not run-verified in this
environment** (no Docker daemon available) — see the README's Limitations
section. Review `docker-compose.yml`, `backend/Dockerfile`,
`frontend/Dockerfile`, and `backend/docker-entrypoint.sh` before relying on
them, and expect to debug on first run.

Order of operations `docker compose up --build` performs:
1. Postgres starts, `docker/init-citext.sql` enables the `citext` extension.
2. Backend container's entrypoint (`docker-entrypoint.sh`) polls the DB
   until reachable, then runs `alembic upgrade head`, then starts uvicorn.
3. Frontend container serves the Next.js standalone build.

The ML model registry (`ml/inference/registry/`) is mounted **read-only**
into the backend container rather than baked into the image — it's a
training *output*, produced by running `ml/training/train.py` separately
(locally, or as a future CI/CD "training" job), so promoting a newly
trained model doesn't require rebuilding the backend image.

## Environment variables required in any deployment

See `.env.example` at the repo root. At minimum, override `SECRET_KEY` and
`CORS_ORIGINS` for anything beyond local development — the shipped defaults
are explicitly dev-only.

## What a real cloud deployment would add (not implemented here)

Per the original spec (section 28): *"Do not implement deployment to a paid
cloud service unless credentials are provided."* None were, so this section
is deliberately a plan, not an implementation:

- **Database**: managed Postgres (RDS/Cloud SQL) instead of the
  `postgres:16` container, with automated backups.
- **Secrets**: a real secrets manager instead of `.env` files.
- **TLS**: terminate HTTPS at a load balancer or Nginx (an `nginx` reverse
  proxy is anticipated by the spec's tech stack but not configured in this
  snapshot — CORS + direct container ports are used for local dev instead).
- **Horizontal scaling**: the backend is stateless (JWT auth, no in-memory
  session) so it can already run as multiple replicas behind a load
  balancer without code changes; the ML model registry would need to move
  from a local mounted volume to shared/object storage (S3 etc.) so every
  replica sees the same production model.
- **Redis**: for JWT blacklisting and rate limiting (see docs/security.md).
- **CI/CD deployment step**: `.github/workflows/ci.yml` currently validates
  (lint, test, build) but does not deploy anywhere — intentionally, per the
  spec constraint above.
