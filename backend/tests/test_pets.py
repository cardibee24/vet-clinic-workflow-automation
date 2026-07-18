import uuid
from datetime import datetime

import pytest


@pytest.fixture()
def auth_headers(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def pet(client, auth_headers):
    create_owner = client.post(
        "/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers
    )
    owner_id = create_owner.json()["id"]
    create_pet = client.post(
        f"/api/owners/{owner_id}/pets",
        json={"name": "Rex", "species": "dog"},
        headers=auth_headers,
    )
    return create_pet.json()


def test_list_pets_requires_auth(client):
    response = client.get("/api/pets")
    assert response.status_code == 401


def test_list_pets(client, auth_headers, pet):
    response = client.get("/api/pets", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert pet["id"] in [p["id"] for p in body]


def test_delete_pet_without_appointments_succeeds(client, auth_headers, pet):
    response = client.delete(f"/api/pets/{pet['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get("/api/pets", headers=auth_headers)
    assert pet["id"] not in [p["id"] for p in response.json()]


def test_delete_pet_requires_auth(client, pet):
    response = client.delete(f"/api/pets/{pet['id']}")
    assert response.status_code == 401


def test_delete_pet_not_found(client, auth_headers):
    response = client.delete(f"/api/pets/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_pet_blocked_by_existing_appointment(client, auth_headers, pet):
    client.post(
        "/api/appointments",
        json={"pet_id": pet["id"], "scheduled_at": datetime(2026, 8, 1, 9, 0, 0).isoformat()},
        headers=auth_headers,
    )

    response = client.delete(f"/api/pets/{pet['id']}", headers=auth_headers)
    assert response.status_code == 409
