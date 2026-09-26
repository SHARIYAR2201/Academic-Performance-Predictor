# Security

## Authentication
- Passwords hashed with bcrypt via `passlib` (`app/core/security.py`),
  never stored or logged in plaintext.
- JWT access + refresh tokens (HS256), short-lived access tokens (30 min
  default) to limit the blast radius of a leaked token.
- `SECRET_KEY` is read from environment/`.env`, never hard-coded — the
  default in `config.py` is explicitly named `CHANGE_ME_IN_PRODUCTION` and
  intended only for local dev.

## Authorization (RBAC)
Enforced at the service layer, not just route decorators — see
[docs/api.md](api.md#role-based-access-control) and
`tests/backend/test_rbac.py` for the automated proof that an instructor
cannot write data for a course they don't teach, and a student cannot
write any academic record or view another student's data.

## Input validation
Every request body is a typed Pydantic model (`app/schemas/`) — invalid
types, missing required fields, and out-of-range values (e.g. negative
scores) are rejected by FastAPI before reaching application code. Beyond
type validation, PostgreSQL-level `CHECK` constraints
(`docs/database.md`) enforce business invariants (score ≤ maximum_score,
attendance percentages 0–100, GPA within 0.0–4.0) so an invariant can't be
violated even by a bug in application-layer validation — verified by
`scripts/smoke_test_models.py`.

## SQL injection
All queries go through SQLAlchemy's query builder (`select(...)`) with
bound parameters — no raw string-interpolated SQL anywhere in the
application code.

## CORS
Configured via `CORS_ORIGINS` in settings (`app/main.py`), defaulting to
`http://localhost:3000` for local dev. Must be restricted to the actual
frontend origin(s) in production — it is **not** wildcarded.

## Secure headers
A middleware in `app/main.py` sets `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY`, and `Referrer-Policy: strict-origin-when-cross-origin`
on every response — verified live (see Phase 3 verification).

## Rate limiting
Not implemented in this snapshot. The architecture anticipates a Redis
service for this (see `docker-compose.yml` comments / README future work);
it is not silently claimed as done.

## What's intentionally NOT done yet (documented, not hidden)
- No server-side JWT revocation/blacklist — logout is stateless.
- No email verification or password-reset flow implemented (architecture
  anticipated in the original spec's section 6, not built in this snapshot).
- No rate limiting on auth endpoints (brute-force protection).
- Secrets are read from `.env` / environment variables; no integration with
  a secrets manager (Vault, AWS Secrets Manager, etc.) — appropriate for
  local dev, a real deployment should add one.

## Never exposed
- Password hashes are excluded from every response schema (`UserOut` has no
  `password_hash` field) — confirmed by `test_register_and_login_succeeds`.
- Database credentials and `SECRET_KEY` are never returned in any API
  response or logged.
