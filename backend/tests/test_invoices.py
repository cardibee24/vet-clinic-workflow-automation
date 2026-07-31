import uuid
from datetime import datetime

import pytest

from app.models.appointment import Appointment
from app.models.owner import Owner
from app.models.pet import Pet
from app.schemas.invoice import LineItemCreate


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


def test_create_invoice_with_appointment_auto_drafts_line_items(client, auth_headers, db_session, owner, appointment, monkeypatch):
    appointment.visit_notes = "Checkup, diagnosed with ear mites"
    appointment.prescription = "Antifungal cream"
    db_session.flush()

    def fake_draft_line_items(notes, catalog):
        assert "Checkup, diagnosed with ear mites" in notes
        assert "Antifungal cream" in notes
        return [
            LineItemCreate(description="Consultation fee", quantity=1, unit_price_cents=5000),
            LineItemCreate(description="Antifungal cream", quantity=1, unit_price_cents=1500),
        ]

    monkeypatch.setattr("app.services.invoice_drafting.draft_line_items", fake_draft_line_items)

    create = client.post(
        "/api/invoices",
        json={"owner_id": str(owner.id), "appointment_id": str(appointment.id)},
        headers=auth_headers,
    )
    assert create.status_code == 201
    invoice_id = create.json()["id"]

    response = client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    descriptions = {item["description"] for item in response.json()["line_items"]}
    assert descriptions == {"Consultation fee", "Antifungal cream"}


def test_create_invoice_with_appointment_without_notes_has_no_line_items(client, auth_headers, owner, appointment):
    create = client.post(
        "/api/invoices",
        json={"owner_id": str(owner.id), "appointment_id": str(appointment.id)},
        headers=auth_headers,
    )
    assert create.status_code == 201
    invoice_id = create.json()["id"]

    response = client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert response.json()["line_items"] == []


def test_create_invoice_auto_draft_failure_does_not_block_creation(
    client, auth_headers, db_session, owner, appointment, monkeypatch
):
    appointment.visit_notes = "Checkup, diagnosed with ear mites"
    db_session.flush()

    def fake_draft_line_items(notes, catalog):
        raise RuntimeError("no API key configured")

    monkeypatch.setattr("app.services.invoice_drafting.draft_line_items", fake_draft_line_items)

    create = client.post(
        "/api/invoices",
        json={"owner_id": str(owner.id), "appointment_id": str(appointment.id)},
        headers=auth_headers,
    )
    assert create.status_code == 201
    invoice_id = create.json()["id"]

    response = client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert response.json()["line_items"] == []


def test_retry_auto_draft_backfills_line_items(client, auth_headers, db_session, owner, appointment, monkeypatch):
    create = client.post(
        "/api/invoices",
        json={"owner_id": str(owner.id), "appointment_id": str(appointment.id)},
        headers=auth_headers,
    )
    invoice_id = create.json()["id"]

    # Notes only get written after the invoice already exists (e.g. vet finishes charting later).
    appointment.visit_notes = "Checkup, diagnosed with ear mites"
    appointment.prescription = "Antifungal cream"
    db_session.flush()

    def fake_draft_line_items(notes, catalog):
        return [LineItemCreate(description="Antifungal cream", quantity=1, unit_price_cents=1500)]

    monkeypatch.setattr("app.services.invoice_drafting.draft_line_items", fake_draft_line_items)

    response = client.post(f"/api/invoices/{invoice_id}/auto-draft-line-items", headers=auth_headers)
    assert response.status_code == 200
    descriptions = {item["description"] for item in response.json()["line_items"]}
    assert descriptions == {"Antifungal cream"}


def test_retry_auto_draft_is_noop_when_notes_unchanged(client, auth_headers, db_session, owner, appointment, monkeypatch):
    appointment.visit_notes = "Checkup, diagnosed with ear mites"
    db_session.flush()

    calls = []

    def fake_draft_line_items(notes, catalog):
        calls.append(notes)
        return [LineItemCreate(description="Consultation fee", quantity=1, unit_price_cents=5000)]

    monkeypatch.setattr("app.services.invoice_drafting.draft_line_items", fake_draft_line_items)

    create = client.post(
        "/api/invoices",
        json={"owner_id": str(owner.id), "appointment_id": str(appointment.id)},
        headers=auth_headers,
    )
    invoice_id = create.json()["id"]
    assert len(calls) == 1  # drafted once at creation

    # Notes haven't changed since - a sync call should be a no-op.
    response = client.post(f"/api/invoices/{invoice_id}/auto-draft-line-items", headers=auth_headers)
    assert response.status_code == 200
    assert len(calls) == 1
    descriptions = {item["description"] for item in response.json()["line_items"]}
    assert descriptions == {"Consultation fee"}


def test_retry_auto_draft_syncs_when_notes_change_without_duplicating(
    client, auth_headers, db_session, owner, appointment, monkeypatch
):
    appointment.visit_notes = "Checkup, diagnosed with ear mites"
    db_session.flush()

    monkeypatch.setattr(
        "app.services.invoice_drafting.draft_line_items",
        lambda notes, catalog: [LineItemCreate(description="Consultation fee", quantity=1, unit_price_cents=5000)],
    )

    create = client.post(
        "/api/invoices",
        json={"owner_id": str(owner.id), "appointment_id": str(appointment.id)},
        headers=auth_headers,
    )
    invoice_id = create.json()["id"]

    # Staff adds a manual charge on top of the AI-drafted one.
    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Manual charge", "quantity": 1, "unit_price_cents": 2000},
        headers=auth_headers,
    )

    # Vet adds more to the notes after the invoice already has line items.
    appointment.visit_notes = "Checkup, diagnosed with ear mites. Gave antifungal cream."
    db_session.flush()

    monkeypatch.setattr(
        "app.services.invoice_drafting.draft_line_items",
        lambda notes, catalog: [
            LineItemCreate(description="Consultation fee", quantity=1, unit_price_cents=5000),
            LineItemCreate(description="Antifungal cream", quantity=1, unit_price_cents=1500),
        ],
    )

    response = client.post(f"/api/invoices/{invoice_id}/auto-draft-line-items", headers=auth_headers)
    assert response.status_code == 200
    descriptions = {item["description"] for item in response.json()["line_items"]}
    # Consultation fee isn't duplicated; the manual charge is untouched; the new item is added.
    assert descriptions == {"Consultation fee", "Manual charge", "Antifungal cream"}

    # Calling again with the same notes is a no-op - no duplicate items appear.
    response2 = client.post(f"/api/invoices/{invoice_id}/auto-draft-line-items", headers=auth_headers)
    descriptions2 = [item["description"] for item in response2.json()["line_items"]]
    assert len(descriptions2) == len(set(descriptions2)) == 3


def test_retry_auto_draft_not_found(client, auth_headers):
    response = client.post(f"/api/invoices/{uuid.uuid4()}/auto-draft-line-items", headers=auth_headers)
    assert response.status_code == 404


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
    listed = next(invoice for invoice in body if invoice["id"] == invoice_id)
    assert listed["total_cents"] == 0


def test_list_invoices_includes_total_cents(client, auth_headers, owner):
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

    response = client.get("/api/invoices", headers=auth_headers)
    assert response.status_code == 200
    listed = next(invoice for invoice in response.json() if invoice["id"] == invoice_id)
    assert listed["total_cents"] == 10000


def test_common_line_items_ranked_by_frequency(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    for unit_price in (5000, 5000, 5000, 7000):
        client.post(
            f"/api/invoices/{invoice_id}/line-items",
            json={"description": "Exam fee", "quantity": 1, "unit_price_cents": unit_price},
            headers=auth_headers,
        )
    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Vaccine", "quantity": 1, "unit_price_cents": 2500},
        headers=auth_headers,
    )

    response = client.get("/api/invoices/common-line-items", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body[0]["description"] == "Exam fee"
    assert body[0]["unit_price_cents"] == 5000
    assert any(item["description"] == "Vaccine" for item in body)


def test_common_line_items_requires_auth(client):
    response = client.get("/api/invoices/common-line-items")
    assert response.status_code == 401


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


def test_delete_invoice_allowed_when_issued(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    )
    client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=auth_headers)

    response = client.delete(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert response.status_code == 404


def test_delete_invoice_allowed_when_paid(client, auth_headers, owner):
    create = client.post("/api/invoices", json={"owner_id": str(owner.id)}, headers=auth_headers)
    invoice_id = create.json()["id"]
    client.post(
        f"/api/invoices/{invoice_id}/line-items",
        json={"description": "Exam fee", "quantity": 1, "unit_price_cents": 5000},
        headers=auth_headers,
    )
    client.patch(f"/api/invoices/{invoice_id}/status", json={"status": "issued"}, headers=auth_headers)
    client.patch(
        f"/api/invoices/{invoice_id}/status",
        json={"status": "paid", "payment_method": "cash"},
        headers=auth_headers,
    )

    response = client.delete(f"/api/invoices/{invoice_id}", headers=auth_headers)
    assert response.status_code == 204


def test_draft_line_items(client, auth_headers, monkeypatch):
    def fake_draft_line_items(notes, catalog):
        assert notes == "Gave rabies vaccine"
        return [LineItemCreate(description="Rabies vaccine", quantity=1, unit_price_cents=4500)]

    monkeypatch.setattr("app.api.invoices.draft_line_items", fake_draft_line_items)

    response = client.post(
        "/api/invoices/draft-line-items",
        json={"notes": "Gave rabies vaccine"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json() == [{"description": "Rabies vaccine", "quantity": 1, "unit_price_cents": 4500}]


def test_draft_line_items_requires_auth(client):
    response = client.post("/api/invoices/draft-line-items", json={"notes": "Gave rabies vaccine"})
    assert response.status_code == 401


def test_draft_line_items_returns_503_on_llm_failure(client, auth_headers, monkeypatch):
    def fake_draft_line_items(notes, catalog):
        raise RuntimeError("no API key configured")

    monkeypatch.setattr("app.api.invoices.draft_line_items", fake_draft_line_items)

    response = client.post(
        "/api/invoices/draft-line-items",
        json={"notes": "Gave rabies vaccine"},
        headers=auth_headers,
    )
    assert response.status_code == 503
