-- Runs automatically on first container startup (docker-entrypoint-initdb.d).
-- The users.email column uses CITEXT for case-insensitive uniqueness; the
-- extension must exist before Alembic's migration runs CREATE EXTENSION
-- IF NOT EXISTS citext (which it also does, so this is defense-in-depth
-- for anyone who connects manually before migrations run).
CREATE EXTENSION IF NOT EXISTS citext;
