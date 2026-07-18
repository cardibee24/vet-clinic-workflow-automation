def test_login_success(client, user):
    response = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client, user):
    response = client.post("/api/auth/login", json={"email": user.email, "password": "wrong"})
    assert response.status_code == 401


def test_login_unknown_email(client, db_session):
    response = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert response.status_code == 401


def test_login_inactive_user_rejected(client, db_session, user):
    user.is_active = False
    db_session.flush()
    response = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_rejects_garbage_token(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_me_returns_current_user(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == user.email
    assert body["id"] == str(user.id)
