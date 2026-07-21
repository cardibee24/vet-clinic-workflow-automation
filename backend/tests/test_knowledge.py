import pytest

from app.ai.knowledge_qa import retrieve_chunks
from app.schemas.knowledge import AskResponse


@pytest.fixture()
def auth_headers(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": "hunter2"})
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_ask(client, auth_headers, monkeypatch):
    def fake_answer_question(db, question):
        assert question == "What's the cancellation fee?"
        return AskResponse(
            answer="It's $35 if cancelled less than 4 hours before the appointment.",
            sources=["cancellation_policy"],
        )

    monkeypatch.setattr("app.api.knowledge.answer_question", fake_answer_question)

    response = client.post(
        "/api/knowledge/ask",
        json={"question": "What's the cancellation fee?"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "It's $35 if cancelled less than 4 hours before the appointment."
    assert body["sources"] == ["cancellation_policy"]


def test_ask_requires_auth(client):
    response = client.post("/api/knowledge/ask", json={"question": "What's the cancellation fee?"})
    assert response.status_code == 401


def test_ask_returns_503_on_failure(client, auth_headers, monkeypatch):
    def fake_answer_question(db, question):
        raise RuntimeError("no API key configured")

    monkeypatch.setattr("app.api.knowledge.answer_question", fake_answer_question)

    response = client.post(
        "/api/knowledge/ask",
        json={"question": "What's the cancellation fee?"},
        headers=auth_headers,
    )
    assert response.status_code == 503


def test_retrieve_chunks_finds_relevant_document(db_session):
    """Real retrieval (no mocking) - the "search" half of RAG. Assumes
    `python -m app.ai.knowledge_ingest` has been run against this database."""
    chunks = retrieve_chunks(db_session, "How much is the fee if I cancel my appointment last minute?", top_k=3)
    assert any(chunk.document == "cancellation_policy" for chunk in chunks)
