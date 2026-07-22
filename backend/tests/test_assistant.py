from datetime import datetime, timedelta

import pytest

from app.ai.assistant_graph import _is_slot_taken, _suggest_available_times
from app.models.appointment import Appointment, AppointmentStatus
from app.models.owner import Owner
from app.models.pet import Pet


@pytest.fixture()
def auth_headers(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_assistant_policy_intent(client, auth_headers, monkeypatch):
    def fake_run_assistant(db, message):
        assert message == "what's the cancellation fee?"
        return {"intent": "policy", "reply": "It's $35 for a late cancellation."}

    monkeypatch.setattr("app.api.assistant.run_assistant", fake_run_assistant)

    response = client.post(
        "/api/assistant",
        json={"message": "what's the cancellation fee?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "policy"
    assert body["reply"] == "It's $35 for a late cancellation."


def test_assistant_booking_intent(client, auth_headers, monkeypatch):
    def fake_run_assistant(db, message):
        return {"intent": "booking", "reply": "Tuesday at 2pm is available."}

    monkeypatch.setattr("app.api.assistant.run_assistant", fake_run_assistant)

    response = client.post(
        "/api/assistant",
        json={"message": "is Tuesday at 2pm free?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "booking"


def test_assistant_triage_intent(client, auth_headers, monkeypatch):
    def fake_run_assistant(db, message):
        return {"intent": "triage", "reply": "Tier 1. Matches collapse/seizure criteria."}

    monkeypatch.setattr("app.api.assistant.run_assistant", fake_run_assistant)

    response = client.post(
        "/api/assistant",
        json={"message": "my dog is having a seizure"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "triage"


def test_assistant_requires_auth(client):
    response = client.post("/api/assistant", json={"message": "hello"})
    assert response.status_code == 401


def test_assistant_returns_503_on_failure(client, auth_headers, monkeypatch):
    def fake_run_assistant(db, message):
        raise RuntimeError("no API key configured")

    monkeypatch.setattr("app.api.assistant.run_assistant", fake_run_assistant)

    response = client.post(
        "/api/assistant",
        json={"message": "hello"},
        headers=auth_headers,
    )
    assert response.status_code == 503


def test_availability_logic_finds_taken_slot_and_open_alternatives(db_session):
    """Real availability logic (no mocking, no LLM call) - the code-decision
    half of the booking branch."""
    owner = Owner(first_name="Jane", last_name="Doe")
    db_session.add(owner)
    db_session.flush()
    pet = Pet(owner_id=owner.id, name="Rex", species="dog")
    db_session.add(pet)
    db_session.flush()

    taken_time = datetime(2026, 8, 4, 14, 0, 0)  # a Tuesday, 2pm
    db_session.add(Appointment(pet_id=pet.id, scheduled_at=taken_time, status=AppointmentStatus.SCHEDULED))
    db_session.flush()

    assert _is_slot_taken(db_session, taken_time) is True
    assert _is_slot_taken(db_session, taken_time + timedelta(hours=2)) is False

    alternatives = _suggest_available_times(db_session, taken_time)
    assert taken_time not in alternatives
    assert all(alt > taken_time for alt in alternatives)


def test_cancelled_appointment_does_not_block_the_slot(db_session):
    owner = Owner(first_name="Jane", last_name="Doe")
    db_session.add(owner)
    db_session.flush()
    pet = Pet(owner_id=owner.id, name="Rex", species="dog")
    db_session.add(pet)
    db_session.flush()

    slot_time = datetime(2026, 8, 4, 15, 0, 0)
    db_session.add(Appointment(pet_id=pet.id, scheduled_at=slot_time, status=AppointmentStatus.CANCELLED))
    db_session.flush()

    assert _is_slot_taken(db_session, slot_time) is False
