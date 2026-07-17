import uuid

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


def test_create_owner(client, auth_headers, user):
    response = client.post(
        "/api/owners",
        json={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com", "phone": "555-1234"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["first_name"] == "Jane"
    assert body["clinic_id"] == str(user.clinic_id)


def test_create_owner_requires_auth(client):
    response = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"})
    assert response.status_code == 401


def test_list_owners_scoped_to_clinic(client, db_session, auth_headers, user):
    owner_a = Owner(clinic_id=user.clinic_id, first_name="Jane", last_name="Doe")
    db_session.add(owner_a)
    db_session.flush()

    response = client.get("/api/owners", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(owner_a.id)


def test_list_owners_excludes_other_clinics(client, auth_headers, other_clinic_headers):
    client.post("/api/owners", json={"first_name": "Other", "last_name": "Owner"}, headers=other_clinic_headers)

    response = client.get("/api/owners", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_owner_includes_pets(client, auth_headers):
    create = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)
    owner_id = create.json()["id"]
    client.post(
        f"/api/owners/{owner_id}/pets",
        json={"name": "Rex", "species": "dog"},
        headers=auth_headers,
    )

    response = client.get(f"/api/owners/{owner_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == owner_id
    assert len(body["pets"]) == 1
    assert body["pets"][0]["name"] == "Rex"
    assert body["pets"][0]["owner_id"] == owner_id


def test_get_owner_not_found(client, auth_headers):
    response = client.get(f"/api/owners/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_get_owner_rejects_cross_tenant_access(client, auth_headers, other_clinic_headers):
    create = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)
    owner_id = create.json()["id"]

    response = client.get(f"/api/owners/{owner_id}", headers=other_clinic_headers)
    assert response.status_code == 404


def test_add_pet_to_owner(client, auth_headers, user):
    create = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)
    owner_id = create.json()["id"]

    response = client.post(
        f"/api/owners/{owner_id}/pets",
        json={"name": "Rex", "species": "dog", "breed": "Lab"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Rex"
    assert body["owner_id"] == owner_id
    assert body["clinic_id"] == str(user.clinic_id)


def test_add_pet_to_nonexistent_owner_returns_404(client, auth_headers):
    response = client.post(
        f"/api/owners/{uuid.uuid4()}/pets",
        json={"name": "Rex", "species": "dog"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_add_pet_rejects_cross_tenant_owner(client, auth_headers, other_clinic_headers):
    create = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)
    owner_id = create.json()["id"]

    response = client.post(
        f"/api/owners/{owner_id}/pets",
        json={"name": "Rex", "species": "dog"},
        headers=other_clinic_headers,
    )
    assert response.status_code == 404
