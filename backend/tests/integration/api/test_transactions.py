"""
Integration tests for transactions API endpoints.

Tests cover:
1. Create transaction endpoint
2. Idempotency
3. Status change endpoint
4. Input validation
5. Edge cases
"""
from __future__ import annotations

import ast
import logging
from uuid import uuid4

import pytest

from app.domain.correlation import IDEMPOTENCY_KEY_HEADER, TRANSACTION_ID_HEADER


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
# Create transaction
# ---------------------------------------------------------------------------


def test_create_transaction_sets_headers_and_logs_event(client, caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)
    user_id = str(uuid4())

    resp = client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "10.50", "tipo": "ingreso"},
        headers={"X-Request-Id": "req-123"},
    )

    assert resp.status_code == 201
    body = resp.json()

    assert resp.headers.get("X-Request-Id") == "req-123"
    assert resp.headers.get(TRANSACTION_ID_HEADER) == body["id"]
    assert body["user_id"] == user_id
    assert body["status"] == "pendiente"

    events = _event_dicts(caplog)
    assert any(e.get("event") == "transaction.created" for e in events)
    created = next(e for e in events if e.get("event") == "transaction.created")
    assert created.get("transaction_id") == body["id"]
    assert created.get("user_id") == user_id


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


def test_create_transaction_is_idempotent(client, caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)
    user_id = str(uuid4())

    resp1 = client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "5.00", "tipo": "egreso"},
        headers={IDEMPOTENCY_KEY_HEADER: "idem-1"},
    )
    assert resp1.status_code == 201
    tx_id_1 = resp1.json()["id"]
    assert resp1.headers.get(IDEMPOTENCY_KEY_HEADER) == "idem-1"
    assert resp1.headers.get(TRANSACTION_ID_HEADER) == tx_id_1

    # Retry with the same key (even if payload differs): should return same tx.
    resp2 = client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "999.00", "tipo": "egreso"},
        headers={IDEMPOTENCY_KEY_HEADER: "idem-1"},
    )
    assert resp2.status_code == 201
    tx_id_2 = resp2.json()["id"]
    assert tx_id_2 == tx_id_1
    assert resp2.headers.get(IDEMPOTENCY_KEY_HEADER) == "idem-1"
    assert resp2.headers.get(TRANSACTION_ID_HEADER) == tx_id_1

    # Only the first request should emit the created event.
    created_count = sum(1 for e in _event_dicts(caplog) if e.get("event") == "transaction.created")
    assert created_count == 1


def test_idempotency_key_is_optional(client) -> None:  # type: ignore[no-untyped-def]
    """Creating transactions without idempotency key should work (but creates new tx each time)."""
    user_id = str(uuid4())

    resp1 = client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "10.00", "tipo": "ingreso"},
    )
    resp2 = client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "10.00", "tipo": "ingreso"},
    )

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["id"] != resp2.json()["id"]  # Different transactions


# ---------------------------------------------------------------------------
# Status change
# ---------------------------------------------------------------------------


def test_change_transaction_status_logs_status_changed(client, caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)
    user_id = str(uuid4())

    resp = client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "12.00", "tipo": "ingreso"},
    )
    tx_id = resp.json()["id"]

    resp2 = client.patch(f"/transactions/{tx_id}/status", json={"status": "procesado"})
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["id"] == tx_id
    assert body2["status"] == "procesado"
    assert resp2.headers.get(TRANSACTION_ID_HEADER) == tx_id

    events = _event_dicts(caplog)
    assert any(e.get("event") == "transaction.status_changed" for e in events)
    changed = next(e for e in events if e.get("event") == "transaction.status_changed")
    assert changed.get("transaction_id") == tx_id
    assert changed.get("old_status") == "pendiente"
    assert changed.get("new_status") == "procesado"


def test_change_status_on_nonexistent_transaction_returns_404(client) -> None:  # type: ignore[no-untyped-def]
    """Status change on non-existent transaction should return 404."""
    fake_id = str(uuid4())
    resp = client.patch(f"/transactions/{fake_id}/status", json={"status": "procesado"})
    assert resp.status_code == 404


def test_change_status_rejects_invalid_status(client) -> None:  # type: ignore[no-untyped-def]
    """Status change with invalid status value should return 422."""
    user_id = str(uuid4())
    resp = client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "10.00", "tipo": "ingreso"},
    )
    tx_id = resp.json()["id"]

    resp2 = client.patch(f"/transactions/{tx_id}/status", json={"status": "invalid_status"})
    assert resp2.status_code == 422


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("monto", ["0", "-1", "-100.50"])
def test_create_transaction_rejects_non_positive_monto(client, monto: str) -> None:  # type: ignore[no-untyped-def]
    """Validation: monto must be > 0."""
    resp = client.post(
        "/transactions/create",
        json={"user_id": str(uuid4()), "monto": monto, "tipo": "ingreso"},
    )
    assert resp.status_code == 422  # Unprocessable Entity


def test_create_transaction_rejects_invalid_tipo(client) -> None:  # type: ignore[no-untyped-def]
    """Validation: tipo must be 'ingreso' or 'egreso'."""
    resp = client.post(
        "/transactions/create",
        json={"user_id": str(uuid4()), "monto": "10.00", "tipo": "invalid_type"},
    )
    assert resp.status_code == 422


def test_create_transaction_rejects_invalid_user_id(client) -> None:  # type: ignore[no-untyped-def]
    """Validation: user_id must be a valid UUID."""
    resp = client.post(
        "/transactions/create",
        json={"user_id": "not-a-uuid", "monto": "10.00", "tipo": "ingreso"},
    )
    assert resp.status_code == 422


def test_create_transaction_rejects_missing_fields(client) -> None:  # type: ignore[no-untyped-def]
    """Validation: all required fields must be present."""
    # Missing monto
    resp = client.post(
        "/transactions/create",
        json={"user_id": str(uuid4()), "tipo": "ingreso"},
    )
    assert resp.status_code == 422

    # Missing tipo
    resp2 = client.post(
        "/transactions/create",
        json={"user_id": str(uuid4()), "monto": "10.00"},
    )
    assert resp2.status_code == 422

