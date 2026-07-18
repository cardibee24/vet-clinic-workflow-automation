import uuid
from datetime import datetime, timedelta

import pytest

from app.models.owner import Owner
from app.models.pet import Pet


@pytest.fixture()
def auth_headers(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def pet(db_session):
    owner = Owner(first_name="Jane", last_name="Doe")
    db_session.add(owner)
    db_session.flush()
    obj = Pet(owner_id=owner.id, name="Rex", species="dog")
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def pet2(db_session):
    owner = Owner(first_name="John", last_name="Smith")
    db_session.add(owner)
    db_session.flush()
    obj = Pet(owner_id=owner.id, name="Fluffy", species="cat")
    db_session.add(obj)
    db_session.flush()
    return obj


def _scheduled_at() -> datetime:
    return datetime(2026, 8, 1, 9, 0, 0)


def test_create_appointment(client, auth_headers, pet):
    response = client.post(
        "/api/appointments",
        json={
            "pet_id": str(pet.id),
            "scheduled_at": _scheduled_at().isoformat(),
            "reason": "checkup",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["pet_id"] == str(pet.id)
    assert body["status"] == "scheduled"
    assert body["assigned_user_id"] is None


def test_create_appointment_requires_auth(client, pet):
    response = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
    )
    assert response.status_code == 401


def test_create_appointment_rejects_nonexistent_pet(client, auth_headers):
    response = client.post(
        "/api/appointments",
        json={"pet_id": str(uuid.uuid4()), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_appointments(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.get("/api/appointments", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert appointment_id in [appointment["id"] for appointment in body]


def test_get_appointment(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.get(f"/api/appointments/{appointment_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == appointment_id


def test_get_appointment_not_found(client, auth_headers):
    response = client.get(f"/api/appointments/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_update_appointment(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat(), "reason": "checkup"},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    new_time = _scheduled_at() + timedelta(days=1)
    response = client.patch(
        f"/api/appointments/{appointment_id}",
        json={"scheduled_at": new_time.isoformat(), "reason": "follow_up"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scheduled_at"] == new_time.isoformat()
    assert body["reason"] == "follow_up"


def test_update_appointment_requires_auth(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.patch(f"/api/appointments/{appointment_id}", json={"reason": "follow_up"})
    assert response.status_code == 401


def test_update_appointment_not_found(client, auth_headers):
    response = client.patch(
        f"/api/appointments/{uuid.uuid4()}", json={"reason": "follow_up"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_update_appointment_rejects_nonexistent_assigned_user(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.patch(
        f"/api/appointments/{appointment_id}",
        json={"assigned_user_id": str(uuid.uuid4())},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_update_appointment_blocked_when_completed(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]
    client.patch(f"/api/appointments/{appointment_id}/status", json={"status": "checked_in"}, headers=auth_headers)
    client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "in_progress"}, headers=auth_headers
    )
    client.patch(f"/api/appointments/{appointment_id}/status", json={"status": "completed"}, headers=auth_headers)

    response = client.patch(
        f"/api/appointments/{appointment_id}", json={"reason": "follow_up"}, headers=auth_headers
    )
    assert response.status_code == 409


def test_check_in_then_complete_appointment(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    checked_in = client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "checked_in"}, headers=auth_headers
    )
    assert checked_in.status_code == 200
    assert checked_in.json()["status"] == "checked_in"

    in_progress = client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "in_progress"}, headers=auth_headers
    )
    assert in_progress.status_code == 200

    completed = client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "completed"}, headers=auth_headers
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_cancel_scheduled_appointment(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "cancelled"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_status_transition_rejects_invalid_jump(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "completed"}, headers=auth_headers
    )
    assert response.status_code == 409


def test_status_transition_rejects_terminal_state_change(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    client.patch(f"/api/appointments/{appointment_id}/status", json={"status": "cancelled"}, headers=auth_headers)
    response = client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "checked_in"}, headers=auth_headers
    )
    assert response.status_code == 409


def test_status_transition_not_found(client, auth_headers):
    response = client.patch(
        f"/api/appointments/{uuid.uuid4()}/status", json={"status": "checked_in"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_check_in_sets_checked_in_at(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]
    assert create.json()["checked_in_at"] is None

    response = client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "checked_in"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["checked_in_at"] is not None


def test_self_check_in_creates_checked_in_appointment(client, pet):
    response = client.post("/api/appointments/self-check-in", json={"pet_id": str(pet.id), "reason": "checkup"})
    assert response.status_code == 201
    body = response.json()
    assert body["pet_id"] == str(pet.id)
    assert body["status"] == "checked_in"
    assert body["reason"] == "checkup"
    assert body["checked_in_at"] is not None


def test_self_check_in_does_not_require_auth(client, pet):
    response = client.post("/api/appointments/self-check-in", json={"pet_id": str(pet.id)})
    assert response.status_code == 201


def test_self_check_in_rejects_nonexistent_pet(client):
    response = client.post("/api/appointments/self-check-in", json={"pet_id": str(uuid.uuid4())})
    assert response.status_code == 404


def test_self_check_in_appears_in_queue(client, auth_headers, pet):
    create = client.post("/api/appointments/self-check-in", json={"pet_id": str(pet.id)})
    appointment_id = create.json()["id"]

    response = client.get("/api/appointments/queue", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert appointment_id in [entry["appointment_id"] for entry in body["entries"]]


def test_get_queue_orders_by_check_in_time(client, auth_headers, pet, pet2):
    first = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    ).json()
    second = client.post(
        "/api/appointments",
        json={"pet_id": str(pet2.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    ).json()

    # Check in second-created appointment first - it should still get position 1.
    client.patch(f"/api/appointments/{second['id']}/status", json={"status": "checked_in"}, headers=auth_headers)
    client.patch(f"/api/appointments/{first['id']}/status", json={"status": "checked_in"}, headers=auth_headers)

    response = client.get("/api/appointments/queue", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_waiting"] == 2
    assert body["entries"][0]["appointment_id"] == second["id"]
    assert body["entries"][0]["position"] == 1
    assert body["entries"][1]["appointment_id"] == first["id"]
    assert body["entries"][1]["position"] == 2


def test_get_queue_excludes_appointments_in_progress(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    ).json()
    client.patch(f"/api/appointments/{create['id']}/status", json={"status": "checked_in"}, headers=auth_headers)
    client.patch(f"/api/appointments/{create['id']}/status", json={"status": "in_progress"}, headers=auth_headers)

    response = client.get("/api/appointments/queue", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"total_waiting": 0, "entries": []}


def test_get_queue_requires_auth(client):
    response = client.get("/api/appointments/queue")
    assert response.status_code == 401


def test_public_queue_status_for_checked_in_appointment(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    ).json()
    client.patch(f"/api/appointments/{create['id']}/status", json={"status": "checked_in"}, headers=auth_headers)

    response = client.get(f"/api/appointments/{create['id']}/queue")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "checked_in"
    assert body["position"] == 1
    assert body["total_waiting"] == 1


def test_public_queue_status_for_not_yet_checked_in_appointment(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    ).json()

    response = client.get(f"/api/appointments/{create['id']}/queue")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["position"] is None
    assert body["total_waiting"] == 0


def test_public_queue_status_not_found(client):
    response = client.get(f"/api/appointments/{uuid.uuid4()}/queue")
    assert response.status_code == 404


def test_delete_appointment_without_dependents_succeeds(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.delete(f"/api/appointments/{appointment_id}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/api/appointments/{appointment_id}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_appointment_requires_auth(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.delete(f"/api/appointments/{appointment_id}")
    assert response.status_code == 401


def test_delete_appointment_not_found(client, auth_headers):
    response = client.delete(f"/api/appointments/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_appointment_blocked_by_existing_invoice(client, auth_headers, pet):
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_at": _scheduled_at().isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]
    owner_id = pet.owner_id
    client.post(
        "/api/invoices",
        json={"owner_id": str(owner_id), "appointment_id": appointment_id},
        headers=auth_headers,
    )

    response = client.delete(f"/api/appointments/{appointment_id}", headers=auth_headers)
    assert response.status_code == 409
