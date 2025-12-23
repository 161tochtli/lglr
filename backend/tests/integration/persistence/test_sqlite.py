"""
Integration tests for SQLite persistence.

These tests use file-backed SQLite for realistic persistence testing
without requiring Docker.
"""
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.repos.sqlite import SqliteTransactionRepo


def test_sqlite_persists_transaction(sqlite_client: TestClient) -> None:
    """Verify transaction is persisted to SQLite."""
    user_id = str(uuid4())
    resp = sqlite_client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "10.50", "tipo": "ingreso"},
    )
    assert resp.status_code == 201
    body = resp.json()

    # Assert we are actually using the sqlite repo (not in-memory).
    repo = sqlite_client.app.state.transaction_repo
    assert isinstance(repo, SqliteTransactionRepo)

    tx_id = UUID(body["id"])
    got = repo.get(tx_id)
    assert got is not None
    assert str(got.user_id) == user_id
    assert str(got.monto) == "10.50"
    assert got.tipo.value == "ingreso"
    assert got.status.value == "pendiente"


def test_sqlite_idempotency_returns_same_transaction(sqlite_client: TestClient) -> None:
    """Verify idempotency works with SQLite persistence."""
    user_id = str(uuid4())
    resp1 = sqlite_client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "5.00", "tipo": "egreso"},
        headers={"Idempotency-Key": "idem-xyz"},
    )
    assert resp1.status_code == 201
    tx_id_1 = resp1.json()["id"]

    resp2 = sqlite_client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "999.00", "tipo": "egreso"},
        headers={"Idempotency-Key": "idem-xyz"},
    )
    assert resp2.status_code == 201
    tx_id_2 = resp2.json()["id"]

    assert tx_id_2 == tx_id_1


def test_sqlite_status_change_persists(sqlite_client: TestClient) -> None:
    """Verify status change is persisted to SQLite."""
    user_id = str(uuid4())
    resp = sqlite_client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "25.00", "tipo": "ingreso"},
    )
    tx_id = UUID(resp.json()["id"])

    # Change status
    resp2 = sqlite_client.patch(f"/transactions/{tx_id}/status", json={"status": "procesado"})
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "procesado"

    # Verify persisted in SQLite
    repo = sqlite_client.app.state.transaction_repo
    tx = repo.get(tx_id)
    assert tx is not None
    assert tx.status.value == "procesado"

