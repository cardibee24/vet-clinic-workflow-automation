import uuid

from app.core.security import create_access_token


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


def test_me_returns_current_user_scoped_to_own_clinic(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == user.email
    assert body["clinic_id"] == str(user.clinic_id)


def test_me_rejects_token_with_mismatched_clinic_id(client, user):
    # Same user id, but a clinic_id claim that doesn't match the user's real
    # clinic (e.g. a forged/tampered token) - the scoped() lookup must miss.
    forged_token = create_access_token(user_id=user.id, clinic_id=uuid.uuid4())
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged_token}"})
    assert response.status_code == 401
