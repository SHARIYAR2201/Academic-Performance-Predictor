from tests.conftest import register_and_login


def test_register_and_login_succeeds(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Alice", "email": "alice@test.edu", "password": "password123", "role": "admin"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@test.edu"
    assert "password" not in body
    assert "password_hash" not in body

    login = client.post("/api/auth/login", json={"email": "alice@test.edu", "password": "password123"})
    assert login.status_code == 200
    assert "access_token" in login.json()
    assert "refresh_token" in login.json()


def test_duplicate_email_registration_rejected(client):
    payload = {"name": "Alice", "email": "dup@test.edu", "password": "password123", "role": "admin"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["code"] == "email_taken"


def test_login_wrong_password_rejected(client):
    client.post(
        "/api/auth/register",
        json={"name": "Bob", "email": "bob@test.edu", "password": "password123", "role": "instructor"},
    )
    resp = client.post("/api/auth/login", json={"email": "bob@test.edu", "password": "wrongpass"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


def test_me_requires_valid_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "missing_token"


def test_me_returns_current_user(client):
    token, _ = register_and_login(client, "Carol", "carol@test.edu", "password123", "student")
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "carol@test.edu"
    assert resp.json()["role"] == "student"


def test_refresh_token_issues_new_access_token(client):
    _, _ = register_and_login(client, "Dave", "dave@test.edu", "password123", "admin")
    login = client.post("/api/auth/login", json={"email": "dave@test.edu", "password": "password123"})
    refresh_token = login.json()["refresh_token"]

    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_refresh_rejects_garbage_token(client):
    resp = client.post("/api/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_refresh_token"
