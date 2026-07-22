import pytest

from app.ai.triage_graph import run_triage


@pytest.fixture()
def auth_headers(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_triage(client, auth_headers, monkeypatch):
    def fake_run_triage(db, symptoms):
        assert symptoms == "dog is limping and won't bear weight"
        return {"tier": 2, "reasoning": "Matches Tier 2.", "needs_more_info": False, "follow_up_question": None}

    monkeypatch.setattr("app.api.triage.run_triage", fake_run_triage)

    response = client.post(
        "/api/triage",
        json={"symptoms": "dog is limping and won't bear weight"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == 2
    assert body["needs_more_info"] is False


def test_triage_requires_auth(client):
    response = client.post("/api/triage", json={"symptoms": "dog is limping"})
    assert response.status_code == 401


def test_triage_returns_503_on_failure(client, auth_headers, monkeypatch):
    def fake_run_triage(db, symptoms):
        raise RuntimeError("no API key configured")

    monkeypatch.setattr("app.api.triage.run_triage", fake_run_triage)

    response = client.post(
        "/api/triage",
        json={"symptoms": "dog is limping and won't bear weight"},
        headers=auth_headers,
    )
    assert response.status_code == 503


def test_vague_description_short_circuits_before_any_llm_call(db_session):
    """The graph's conditional branch: a description under
    _MIN_DESCRIPTION_LENGTH routes straight to END without ever reaching the
    LLM decision node - no mocking needed to prove this, since the graph
    itself must not call out. ("sick" is 4 chars, well under the 15-char
    threshold - unlike "not feeling good" at 17 chars, which passes the
    length check and would actually call the LLM.)"""
    result = run_triage(db_session, "sick")
    assert result["needs_more_info"] is True
    assert result["follow_up_question"] is not None
    assert result["tier"] is None
