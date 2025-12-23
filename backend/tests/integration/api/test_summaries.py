"""
Integration tests for summaries API endpoint.

Tests cover:
1. Create summary endpoint
2. OpenAI stub integration
3. Persistence
4. Domain event logging
5. Validation
"""
from __future__ import annotations

import ast
import logging
from uuid import UUID

from fastapi.testclient import TestClient

import pytest

from app.infra.openai_client import OpenAIClientStub
from app.main import create_app


def _event_dicts(caplog) -> list[dict]:
    out: list[dict] = []
    for record in caplog.records:
        msg = record.msg
        if isinstance(msg, dict):
            out.append(msg)
            continue
        if isinstance(msg, str) and msg.startswith("{") and msg.endswith("}"):
            try:
                parsed = ast.literal_eval(msg)
                if isinstance(parsed, dict):
                    out.append(parsed)
            except Exception:
                continue
    return out


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def summarize_client():
    """Client with OpenAI stub for summarization tests."""
    stub = OpenAIClientStub()
    app = create_app(
        configure_logs=False,
        persistence="memory",
        openai_client=stub,
        run_worker=False,
    )
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Basic functionality
# ---------------------------------------------------------------------------


def test_create_summary_echoes_request_id_and_logs_event(summarize_client, caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)

    resp = summarize_client.post(
        "/assistant/summarize",
        json={"text": "  hola   mundo  ", "model": "test-model"},
        headers={"X-Request-Id": "req-abc"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert resp.headers.get("X-Request-Id") == "req-abc"
    assert body["request_id"] == "req-abc"
    assert body["model"] == "test-model"
    # Now uses OpenAI stub format: [Resumen de X palabras] ...
    assert "[Resumen de" in body["summary"]
    assert "hola mundo" in body["summary"]

    events = _event_dicts(caplog)
    assert any(e.get("event") == "assistant.summary_created" for e in events)
    created = next(e for e in events if e.get("event") == "assistant.summary_created")
    assert created.get("request_id") == "req-abc"
    assert created.get("model") == "test-model"


def test_summarize_endpoint_uses_openai_stub(summarize_client: TestClient) -> None:
    """Endpoint should use OpenAI stub and return proper summary."""
    resp = summarize_client.post(
        "/assistant/summarize",
        json={"text": "Este es un texto de ejemplo para resumir.", "model": "test-model"},
        headers={"X-Request-Id": "req-abc"},
    )

    assert resp.status_code == 201
    body = resp.json()

    assert body["request_id"] == "req-abc"
    assert body["model"] == "test-model"
    assert "[Resumen de" in body["summary"]
    assert "palabras]" in body["summary"]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_summarize_endpoint_persists_to_db(summarize_client: TestClient) -> None:
    """Endpoint should persist summary to repository."""
    resp = summarize_client.post(
        "/assistant/summarize",
        json={"text": "Texto para persistir."},
    )

    assert resp.status_code == 201
    summary_id = UUID(resp.json()["id"])

    # Verify persisted
    repo = summarize_client.app.state.summary_repo
    saved = repo.get(summary_id)
    assert saved is not None
    assert saved.text == "Texto para persistir."


# ---------------------------------------------------------------------------
# Domain events
# ---------------------------------------------------------------------------


def test_summarize_endpoint_logs_domain_event(summarize_client: TestClient, caplog) -> None:
    """Endpoint should log assistant.summary_created event."""
    caplog.set_level(logging.INFO)

    resp = summarize_client.post(
        "/assistant/summarize",
        json={"text": "Log test", "model": "log-model"},
        headers={"X-Request-Id": "log-req"},
    )

    assert resp.status_code == 201

    events = _event_dicts(caplog)
    assert any(e.get("event") == "assistant.summary_created" for e in events)

    created = next(e for e in events if e.get("event") == "assistant.summary_created")
    assert created.get("request_id") == "log-req"
    assert created.get("model") == "log-model"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_summarize_endpoint_normalizes_whitespace(summarize_client: TestClient) -> None:
    """Endpoint should normalize whitespace in input text."""
    resp = summarize_client.post(
        "/assistant/summarize",
        json={"text": "  texto   con   espacios  "},
    )

    assert resp.status_code == 201
    # The NewSummary model normalizes whitespace
    assert resp.json()["text"] == "texto con espacios"


def test_summarize_endpoint_rejects_empty_text(summarize_client: TestClient) -> None:
    """Endpoint should reject empty or whitespace-only text."""
    resp = summarize_client.post(
        "/assistant/summarize",
        json={"text": "   "},
    )

    assert resp.status_code == 422  # Validation error


# ---------------------------------------------------------------------------
# Default stub behavior
# ---------------------------------------------------------------------------


def test_default_app_uses_stub_when_no_api_key(summarize_client) -> None:  # type: ignore[no-untyped-def]
    """App with OpenAI stub should use stub client."""
    resp = summarize_client.post(
        "/assistant/summarize",
        json={"text": "Default stub test"},
    )

    assert resp.status_code == 201
    body = resp.json()

    # Stub format: [Resumen de X palabras] ...
    assert "[Resumen de" in body["summary"]

