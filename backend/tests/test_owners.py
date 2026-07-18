import uuid

import pytest

from app.models.owner import Owner


@pytest.fixture()
def auth_headers(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_owner(client, auth_headers):
    response = client.post(
        "/api/owners",
        json={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com", "phone": "555-1234"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["first_name"] == "Jane"


def test_create_owner_requires_auth(client):
    response = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"})
    assert response.status_code == 401


def test_list_owners(client, db_session, auth_headers):
    owner_a = Owner(first_name="Jane", last_name="Doe")
    db_session.add(owner_a)
    db_session.flush()

    response = client.get("/api/owners", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert str(owner_a.id) in [owner["id"] for owner in body]


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


def test_add_pet_to_owner(client, auth_headers):
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


def test_add_pet_to_nonexistent_owner_returns_404(client, auth_headers):
    response = client.post(
        f"/api/owners/{uuid.uuid4()}/pets",
        json={"name": "Rex", "species": "dog"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_update_owner(client, auth_headers):
    create = client.post(
        "/api/owners",
        json={"first_name": "Jane", "last_name": "Doe", "phone": "555-1234"},
        headers=auth_headers,
    )
    owner_id = create.json()["id"]

    response = client.patch(
        f"/api/owners/{owner_id}",
        json={"phone": "555-9999"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["phone"] == "555-9999"
    assert body["first_name"] == "Jane"


def test_update_owner_requires_auth(client, auth_headers):
    create = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)
    owner_id = create.json()["id"]

    response = client.patch(f"/api/owners/{owner_id}", json={"phone": "555-9999"})
    assert response.status_code == 401


def test_update_owner_not_found(client, auth_headers):
    response = client.patch(f"/api/owners/{uuid.uuid4()}", json={"phone": "555-9999"}, headers=auth_headers)
    assert response.status_code == 404


def test_delete_owner_without_dependents_succeeds(client, auth_headers):
    create = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)
    owner_id = create.json()["id"]

    response = client.delete(f"/api/owners/{owner_id}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/api/owners/{owner_id}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_owner_requires_auth(client, auth_headers):
    create = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)
    owner_id = create.json()["id"]

    response = client.delete(f"/api/owners/{owner_id}")
    assert response.status_code == 401


def test_delete_owner_not_found(client, auth_headers):
    response = client.delete(f"/api/owners/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_owner_blocked_by_existing_pet(client, auth_headers):
    create = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)
    owner_id = create.json()["id"]
    client.post(f"/api/owners/{owner_id}/pets", json={"name": "Rex", "species": "dog"}, headers=auth_headers)

    response = client.delete(f"/api/owners/{owner_id}", headers=auth_headers)
    assert response.status_code == 409

    response = client.get(f"/api/owners/{owner_id}", headers=auth_headers)
    assert response.status_code == 200


def test_delete_owner_blocked_by_existing_invoice(client, auth_headers):
    create = client.post("/api/owners", json={"first_name": "Jane", "last_name": "Doe"}, headers=auth_headers)
    owner_id = create.json()["id"]
    client.post("/api/invoices", json={"owner_id": owner_id}, headers=auth_headers)

    response = client.delete(f"/api/owners/{owner_id}", headers=auth_headers)
    assert response.status_code == 409
