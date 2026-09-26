import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402

TRUNCATE_TABLES = (
    "users, departments, semesters, datasets"  # CASCADE reaches everything else
)


@pytest.fixture(autouse=True)
def clean_db():
    """Truncates the core tables before every test so each test starts from
    a known-empty state. This uses the real dev Postgres instance rather
    than mocks — these are integration tests by design (spec section 26
    calls for testing auth, RBAC, CRUD, and the prediction endpoint against
    real behavior, not simulated).
    """
    db = SessionLocal()
    db.execute(text(f"TRUNCATE {TRUNCATE_TABLES} CASCADE"))
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.execute(text(f"TRUNCATE {TRUNCATE_TABLES} CASCADE"))
    db.commit()
    db.close()


@pytest.fixture
def client():
    return TestClient(app)


def register_and_login(client: TestClient, name: str, email: str, password: str, role: str) -> tuple[str, int]:
    client.post("/api/auth/register", json={"name": name, "email": email, "password": password, "role": role})
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    token = resp.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    return token, me.json()["id"]
