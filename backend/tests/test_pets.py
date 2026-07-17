import pytest

from app.core.security import hash_password
from app.models.clinic import Clinic
from app.models.owner import Owner
from app.models.user import User, UserRole


@pytest.fixture()
def auth_headers(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def other_clinic_headers(client, db_session):
    other_clinic = Clinic(name="Other Clinic")
    db_session.add(other_clinic)
    db_session.flush()

    other_user = User(
        clinic_id=other_clinic.id,
        email="other-vet@example.com",
        hashed_password=hash_password("hunter2"),
        full_name="Dr. Other",
        role=UserRole.VET,
    )
    db_session.add(other_user)
    db_session.flush()

    login = client.post("/api/auth/login", json={"email": other_user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_pets_requires_auth(client):
    response = client.get("/api/pets")
    assert response.status_code == 401


def test_list_pets_scoped_to_clinic(client, auth_headers, user):
    create_owner = client.post(
        "/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers
    )
    owner_id = create_owner.json()["id"]
    client.post(
        f"/api/owners/{owner_id}/pets",
        json={"name": "Rex", "species": "dog"},
        headers=auth_headers,
    )

    response = client.get("/api/pets", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Rex"
    assert body[0]["clinic_id"] == str(user.clinic_id)


def test_list_pets_excludes_other_clinics(client, auth_headers, other_clinic_headers):
    create_owner = client.post(
        "/api/owners", json={"first_name": "Other", "last_name": "Owner"}, headers=other_clinic_headers
    )
    owner_id = create_owner.json()["id"]
    client.post(
        f"/api/owners/{owner_id}/pets",
        json={"name": "Fido", "species": "dog"},
        headers=other_clinic_headers,
    )

    response = client.get("/api/pets", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []
