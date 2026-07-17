import uuid
from datetime import datetime, timedelta

import pytest

from app.core.security import hash_password
from app.models.clinic import Clinic
from app.models.owner import Owner
from app.models.pet import Pet
from app.models.user import User, UserRole


@pytest.fixture()
def auth_headers(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def other_clinic(db_session):
    obj = Clinic(name="Other Clinic")
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def other_user(db_session, other_clinic):
    obj = User(
        clinic_id=other_clinic.id,
        email="other-vet@example.com",
        hashed_password=hash_password("hunter2"),
        full_name="Dr. Other",
        role=UserRole.VET,
    )
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def other_clinic_headers(client, other_user):
    login = client.post("/api/auth/login", json={"email": other_user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def pet(db_session, user):
    owner = Owner(clinic_id=user.clinic_id, first_name="Jane", last_name="Doe")
    db_session.add(owner)
    db_session.flush()
    obj = Pet(clinic_id=user.clinic_id, owner_id=owner.id, name="Rex", species="dog")
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def other_clinic_pet(db_session, other_user):
    owner = Owner(clinic_id=other_user.clinic_id, first_name="Other", last_name="Owner")
    db_session.add(owner)
    db_session.flush()
    obj = Pet(clinic_id=other_user.clinic_id, owner_id=owner.id, name="Fido", species="dog")
    db_session.add(obj)
    db_session.flush()
    return obj


def _window():
    start = datetime(2026, 8, 1, 9, 0, 0)
    return start, start + timedelta(minutes=30)


def test_create_appointment(client, auth_headers, user, pet):
    start, end = _window()
    response = client.post(
        "/api/appointments",
        json={
            "pet_id": str(pet.id),
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
            "reason": "Annual checkup",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["pet_id"] == str(pet.id)
    assert body["clinic_id"] == str(user.clinic_id)
    assert body["status"] == "scheduled"
    assert body["assigned_user_id"] is None


def test_create_appointment_requires_auth(client, pet):
    start, end = _window()
    response = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
    )
    assert response.status_code == 401


def test_create_appointment_rejects_end_before_start(client, auth_headers, pet):
    start, end = _window()
    response = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_start": end.isoformat(), "scheduled_end": start.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_appointment_rejects_nonexistent_pet(client, auth_headers):
    start, end = _window()
    response = client.post(
        "/api/appointments",
        json={"pet_id": str(uuid.uuid4()), "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_appointment_rejects_cross_tenant_pet(client, auth_headers, other_clinic_pet):
    start, end = _window()
    response = client.post(
        "/api/appointments",
        json={
            "pet_id": str(other_clinic_pet.id),
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_appointment_rejects_cross_tenant_assigned_user(client, auth_headers, pet, other_user):
    start, end = _window()
    response = client.post(
        "/api/appointments",
        json={
            "pet_id": str(pet.id),
            "assigned_user_id": str(other_user.id),
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_appointments_scoped_to_clinic(client, auth_headers, pet):
    start, end = _window()
    client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
        headers=auth_headers,
    )

    response = client.get("/api/appointments", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["pet_id"] == str(pet.id)


def test_list_appointments_excludes_other_clinics(client, auth_headers, other_clinic_headers, other_clinic_pet):
    start, end = _window()
    client.post(
        "/api/appointments",
        json={
            "pet_id": str(other_clinic_pet.id),
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
        },
        headers=other_clinic_headers,
    )

    response = client.get("/api/appointments", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_appointment(client, auth_headers, pet):
    start, end = _window()
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.get(f"/api/appointments/{appointment_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == appointment_id


def test_get_appointment_not_found(client, auth_headers):
    response = client.get(f"/api/appointments/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_get_appointment_rejects_cross_tenant_access(client, auth_headers, other_clinic_headers, pet):
    start, end = _window()
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.get(f"/api/appointments/{appointment_id}", headers=other_clinic_headers)
    assert response.status_code == 404


def test_check_in_then_complete_appointment(client, auth_headers, pet):
    start, end = _window()
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
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
    start, end = _window()
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "cancelled"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_status_transition_rejects_invalid_jump(client, auth_headers, pet):
    start, end = _window()
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "completed"}, headers=auth_headers
    )
    assert response.status_code == 409


def test_status_transition_rejects_terminal_state_change(client, auth_headers, pet):
    start, end = _window()
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
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


def test_status_transition_rejects_cross_tenant(client, auth_headers, other_clinic_headers, pet):
    start, end = _window()
    create = client.post(
        "/api/appointments",
        json={"pet_id": str(pet.id), "scheduled_start": start.isoformat(), "scheduled_end": end.isoformat()},
        headers=auth_headers,
    )
    appointment_id = create.json()["id"]

    response = client.patch(
        f"/api/appointments/{appointment_id}/status", json={"status": "checked_in"}, headers=other_clinic_headers
    )
    assert response.status_code == 404
