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


@pytest.fixture()
def owner(db_session, user):
    obj = Owner(clinic_id=user.clinic_id, first_name="Jane", last_name="Doe")
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def other_owner(db_session, user):
    obj = Owner(clinic_id=user.clinic_id, first_name="Someone", last_name="Else")
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def appointment(db_session, user, owner):
    pet = Pet(clinic_id=user.clinic_id, owner_id=owner.id, name="Rex", species="dog")
    db_session.add(pet)
    db_session.flush()
    start = datetime(2026, 8, 1, 9, 0, 0)
    obj = Appointment(
        clinic_id=user.clinic_id, pet_id=pet.id, scheduled_start=start, scheduled_end=start + timedelta(minutes=30)
    )
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def other_clinic_owner(db_session, other_user):
    obj = Owner(clinic_id=other_user.clinic_id, first_name="Other", last_name="Owner")
    db_session.add(obj)
    db_session.flush()
    return obj


def test_create_invoice(client, auth_headers, user, owner):
    response = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["owner_id"] == str(owner.id)
    assert body["clinic_id"] == str(user.clinic_id)
    assert body["status"] == "draft"
    assert body["appointment_id"] is None


def test_create_invoice_requires_auth(client, owner):
    response = client.post("/api/invoices", json={"owner_id": str(owner.id)})
    assert response.status_code == 401


def test_create_invoice_rejects_nonexistent_owner(client, auth_headers):
    response = client.post("/api/invoices", json={"owner_id": str(uuid.uuid4())}, headers=auth_headers)
    assert response.status_code == 404


def test_create_invoice_rejects_cross_tenant_owner(client, auth_headers, other_clinic_owner):
    response = client.post("/api/invoices", json={"owner_id": str(other_clinic_owner.id)}, headers=auth_headers)
    assert response.status_code == 404


def test_create_invoice_with_appointment(client, auth_headers, owner, appointment):
    response = client.post(
        "/api/invoices",
        json={"owner_id": str(owner.id), "appointment_id": str(appointment.id)},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["appointment_id"] == str(appointment.id)


def test_create_invoice_rejects_appointment_belonging_to_other_owner(
    client, auth_headers, other_owner, appointment
):
    response = client.post(
        "/api/invoices",
        json={"owner_id": str(other_owner.id), "appointment_id": str(appointment.id)},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_list_invoices_scoped_to_clinic(client, auth_headers, owner):
    client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)

    response = client.get("/api/invoices", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["owner_id"] == str(owner.id)


def test_list_invoices_excludes_other_clinics(client, auth_headers, other_clinic_headers, other_clinic_owner):
    client.post("/api/invoices", json={"owner_id": str(other_clinic_owner.id)}, headers=other_clinic_headers)

    response = client.get("/api/invoices", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_invoice_includes_line_items_and_total(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    )
    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Vaccine", "quantity": 2, "unit_price_cents": 2500},
        headers=auth_headers,
    )

    response = client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["line_items"]) == 2
    assert body["line_items"][1]["amount_cents"] == 5000
    assert body["total_cents"] == 10000


def test_get_invoice_not_found(client, auth_headers):
    response = client.get(f"/api/invoices/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_get_invoice_rejects_cross_tenant_access(client, auth_headers, other_clinic_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    response = client.get(f"/api/invoices/{invoice_id}", headers=other_clinic_headers)
    assert response.status_code == 404


def test_add_line_item_rejects_nondraft_invoice(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    )
    client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=auth_headers)

    response = client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Late add", "quantity": 1, "unit_price_cents": 1000},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_add_line_item_rejects_cross_tenant_invoice(client, auth_headers, other_clinic_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    response = client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=other_clinic_headers,
    )
    assert response.status_code == 404


def test_issue_then_pay_invoice(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    )

    issued = client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=auth_headers)
    assert issued.status_code == 200
    assert issued.json()["status"] == "issued"
    assert issued.json()["issued_at"] is not None

    paid = client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "paid"}, headers=auth_headers)
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"


def test_issue_invoice_rejects_empty_line_items(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    response = client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=auth_headers)
    assert response.status_code == 422


def test_void_draft_invoice(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    response = client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "void"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "void"


def test_status_transition_rejects_invalid_jump(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    response = client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "paid"}, headers=auth_headers)
    assert response.status_code == 409


def test_status_transition_rejects_terminal_state_change(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "void"}, headers=auth_headers)
    response = client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=auth_headers)
    assert response.status_code == 409


def test_status_transition_not_found(client, auth_headers):
    response = client.patch(
        f"/api/invoices/{uuid.uuid4()}/status", json={"status": "issued"}, headers=auth_headers
    )
    assert response.status_code == 404


def test_status_transition_rejects_cross_tenant(client, auth_headers, other_clinic_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    response = client.patch(
        f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=other_clinic_headers
    )
    assert response.status_code == 404
