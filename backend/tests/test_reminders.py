import uuid
from datetime import datetime, timedelta

import pytest

from app.core.security import hash_password
from app.models.appointment import Appointment
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


def _window():
    start = datetime(2026, 8, 1, 9, 0, 0)
    return start, start + timedelta(minutes=30)


@pytest.fixture()
def appointment(db_session, user):
    owner = Owner(clinic_id=user.clinic_id, first_name="Jane", last_name="Doe")
    db_session.add(owner)
    db_session.flush()
    pet = Pet(clinic_id=user.clinic_id, owner_id=owner.id, name="Rex", species="dog")
    db_session.add(pet)
    db_session.flush()
    start, end = _window()
    obj = Appointment(clinic_id=user.clinic_id, pet_id=pet.id, scheduled_start=start, scheduled_end=end)
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def other_clinic_appointment(db_session, other_user):
    owner = Owner(clinic_id=other_user.clinic_id, first_name="Other", last_name="Owner")
    db_session.add(owner)
    db_session.flush()
    pet = Pet(clinic_id=other_user.clinic_id, owner_id=owner.id, name="Fido", species="dog")
    db_session.add(pet)
    db_session.flush()
    start, end = _window()
    obj = Appointment(clinic_id=other_user.clinic_id, pet_id=pet.id, scheduled_start=start, scheduled_end=end)
    db_session.add(obj)
    db_session.flush()
    return obj


def test_create_reminder(client, auth_headers, user, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    response = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "email", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["appointment_id"] == str(appointment.id)
    assert body["clinic_id"] == str(user.clinic_id)
    assert body["channel"] == "email"
    assert body["status"] == "pending"
    assert body["sent_at"] is None


def test_create_reminder_requires_auth(client, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    response = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "sms", "send_at": send_at.isoformat()},
    )
    assert response.status_code == 401


def test_create_reminder_rejects_send_at_after_appointment_start(client, auth_headers, appointment):
    send_at = appointment.scheduled_start + timedelta(minutes=5)
    response = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "email", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_create_reminder_rejects_nonexistent_appointment(client, auth_headers):
    response = client.post(
        "/api/reminders",
        json={
            "appointment_id": str(uuid.uuid4()),
            "channel": "email",
            "send_at": datetime(2026, 8, 1, 8, 0, 0).isoformat(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_create_reminder_rejects_cross_tenant_appointment(client, auth_headers, other_clinic_appointment):
    send_at = other_clinic_appointment.scheduled_start - timedelta(hours=1)
    response = client.post(
        "/api/reminders",
        json={
            "appointment_id": str(other_clinic_appointment.id),
            "channel": "email",
            "send_at": send_at.isoformat(),
        },
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_list_reminders_scoped_to_clinic(client, auth_headers, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "email", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )

    response = client.get("/api/reminders", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["appointment_id"] == str(appointment.id)


def test_list_reminders_excludes_other_clinics(
    client, auth_headers, other_clinic_headers, other_clinic_appointment
):
    send_at = other_clinic_appointment.scheduled_start - timedelta(hours=1)
    client.post(
        "/api/reminders",
        json={
            "appointment_id": str(other_clinic_appointment.id),
            "channel": "email",
            "send_at": send_at.isoformat(),
        },
        headers=other_clinic_headers,
    )

    response = client.get("/api/reminders", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_reminder(client, auth_headers, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    create = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "email", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )
    reminder_id = create.json()["id"]

    response = client.get(f"/api/reminders/{reminder_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == reminder_id


def test_get_reminder_not_found(client, auth_headers):
    response = client.get(f"/api/reminders/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_get_reminder_rejects_cross_tenant_access(client, auth_headers, other_clinic_headers, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    create = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "email", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )
    reminder_id = create.json()["id"]

    response = client.get(f"/api/reminders/{reminder_id}", headers=other_clinic_headers)
    assert response.status_code == 404


def test_mark_reminder_sent_sets_sent_at(client, auth_headers, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    create = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "email", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )
    reminder_id = create.json()["id"]

    response = client.patch(f"/api/reminders/{reminder_id}/status", json={"status": "sent"}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "sent"
    assert body["sent_at"] is not None


def test_mark_reminder_failed_then_retry(client, auth_headers, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    create = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "sms", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )
    reminder_id = create.json()["id"]

    failed = client.patch(f"/api/reminders/{reminder_id}/status", json={"status": "failed"}, headers=auth_headers)
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"

    retried = client.patch(
        f"/api/reminders/{reminder_id}/status", json={"status": "pending"}, headers=auth_headers
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "pending"


def test_cancel_pending_reminder(client, auth_headers, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    create = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "email", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )
    reminder_id = create.json()["id"]

    response = client.patch(
        f"/api/reminders/{reminder_id}/status", json={"status": "cancelled"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_status_transition_rejects_invalid_jump(client, auth_headers, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    create = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "email", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )
    reminder_id = create.json()["id"]

    client.patch(f"/api/reminders/{reminder_id}/status", json={"status": "sent"}, headers=auth_headers)
    response = client.patch(
        f"/api/reminders/{reminder_id}/status", json={"status": "pending"}, headers=auth_headers
    )
    assert response.status_code == 409


def test_status_transition_rejects_terminal_state_change(client, auth_headers, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    create = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "email", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )
    reminder_id = create.json()["id"]

    client.patch(f"/api/reminders/{reminder_id}/status", json={"status": "cancelled"}, headers=auth_headers)
    response = client.patch(f"/api/reminders/{reminder_id}/status", json={"status": "sent"}, headers=auth_headers)
    assert response.status_code == 409


def test_status_transition_not_found(client, auth_headers):
    response = client.patch(
        f"/api/reminders/{uuid.uuid4()}/status", json={"status": "sent"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_status_transition_rejects_cross_tenant(client, auth_headers, other_clinic_headers, appointment):
    send_at = appointment.scheduled_start - timedelta(hours=1)
    create = client.post(
        "/api/reminders",
        json={"appointment_id": str(appointment.id), "channel": "email", "send_at": send_at.isoformat()},
        headers=auth_headers,
    )
    reminder_id = create.json()["id"]

    response = client.patch(
        f"/api/reminders/{reminder_id}/status", json={"status": "sent"}, headers=other_clinic_headers
    )
    assert response.status_code == 404
