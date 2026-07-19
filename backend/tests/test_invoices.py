import uuid
from datetime import datetime

import pytest

from app.models.appointment import Appointment
from app.models.owner import Owner
from app.models.pet import Pet


@pytest.fixture()
def auth_headers(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def owner(db_session):
    obj = Owner(first_name="Jane", last_name="Doe")
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def other_owner(db_session):
    obj = Owner(first_name="Someone", last_name="Else")
    db_session.add(obj)
    db_session.flush()
    return obj


@pytest.fixture()
def appointment(db_session, owner):
    pet = Pet(owner_id=owner.id, name="Rex", species="dog")
    db_session.add(pet)
    db_session.flush()
    obj = Appointment(pet_id=pet.id, scheduled_at=datetime(2026, 8, 1, 9, 0, 0))
    db_session.add(obj)
    db_session.flush()
    return obj


def test_create_invoice(client, auth_headers, owner):
    response = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["owner_id"] == str(owner.id)
    assert body["status"] == "draft"
    assert body["appointment_id"] is None


def test_create_invoice_requires_auth(client, owner):
    response = client.post("/api/invoices", json={"owner_id": str(owner.id)})
    assert response.status_code == 401


def test_create_invoice_rejects_nonexistent_owner(client, auth_headers):
    response = client.post("/api/invoices", json={"owner_id": str(uuid.uuid4())}, headers=auth_headers)
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


def test_list_invoices(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    response = client.get("/api/invoices", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert invoice_id in [invoice["id"] for invoice in body]


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


def test_update_line_item(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    line_item = client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    ).json()

    response = client.patch(
        f"/api/invoices/{invoice_id}/line-items/{line_item['id']}",
        json={"quantity": 3, "unit_price_cents": 1000},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Exam fee"
    assert body["quantity"] == 3
    assert body["unit_price_cents"] == 1000
    assert body["amount_cents"] == 3000


def test_update_line_item_rejects_nondraft_invoice(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    line_item = client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    ).json()
    client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=auth_headers)

    response = client.patch(
        f"/api/invoices/{invoice_id}/line-items/{line_item['id']}",
        json={"quantity": 2},
        headers=auth_headers,
    )
    assert response.status_code == 409


def test_update_line_item_not_found(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    response = client.patch(
        f"/api/invoices/{invoice_id}/line-items/{uuid.uuid4()}",
        json={"quantity": 2},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_line_item(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    line_item = client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    ).json()

    response = client.delete(
        f"/api/invoices/{invoice_id}/line-items/{line_item['id']}", headers=auth_headers
    )
    assert response.status_code == 204

    invoice = client.get(f"/api/invoices/{invoice_id}", headers=auth_headers).json()
    assert invoice["line_items"] == []


def test_delete_line_item_rejects_nondraft_invoice(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    line_item = client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    ).json()
    client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=auth_headers)

    response = client.delete(
        f"/api/invoices/{invoice_id}/line-items/{line_item['id']}", headers=auth_headers
    )
    assert response.status_code == 409


def test_delete_line_item_not_found(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    response = client.delete(
        f"/api/invoices/{invoice_id}/line-items/{uuid.uuid4()}", headers=auth_headers
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

    paid = client.patch(
        f"/api/invoices/{invoice_id}/status",
        json={"status": "paid", "payment_method": "card"},
        headers=auth_headers,
    )
    assert paid.status_code == 200
    assert paid.json()["status"] == "paid"
    assert paid.json()["payment_method"] == "card"
    assert paid.json()["paid_at"] is not None


def test_mark_paid_requires_payment_method(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    )
    client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=auth_headers)

    response = client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "paid"}, headers=auth_headers)
    assert response.status_code == 422


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


def test_delete_draft_invoice_succeeds(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    )

    response = client.delete(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_invoice_requires_auth(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]

    response = client.delete(f"/api/invoices/{invoice_id}")
    assert response.status_code == 401


def test_delete_invoice_not_found(client, auth_headers):
    response = client.delete(f"/api/invoices/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_invoice_blocked_once_issued(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    )
    client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=auth_headers)

    response = client.delete(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert response.status_code == 409
