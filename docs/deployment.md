# Deployment

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
