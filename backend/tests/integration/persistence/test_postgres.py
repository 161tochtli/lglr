"""
Integration tests for PostgreSQL persistence.

These tests require PostgreSQL running (via docker-compose or devcontainer).
Skip automatically if DATABASE_URL is not set to a postgres URL.

Run with:
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/legali pytest -k postgres
"""
from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

import pytest

from app.repos.postgres import PostgresTransactionRepo
from conftest import postgres_available


@pytest.mark.postgres
@postgres_available
def test_postgres_persists_transaction(postgres_client: TestClient) -> None:
    """Verify transaction is persisted to Postgres."""
    user_id = str(uuid4())
    resp = postgres_client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "10.50", "tipo": "ingreso"},
    )
    assert resp.status_code == 201
    body = resp.json()

    # Verify repo is Postgres-backed
    app = postgres_client.app
    assert isinstance(app.state.transaction_repo, PostgresTransactionRepo)

    # Read directly from DB to confirm persistence
    tx = app.state.transaction_repo.get(body["id"])
    assert tx is not None
    assert str(tx.user_id) == user_id
    assert tx.status.value == "pendiente"


@pytest.mark.postgres
@postgres_available
def test_postgres_idempotency_returns_same_transaction(postgres_client: TestClient) -> None:
    """Verify idempotency works with Postgres persistence."""
    user_id = str(uuid4())

    resp1 = postgres_client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "5.00", "tipo": "egreso"},
        headers={"Idempotency-Key": "pg-idem-test"},
    )
    assert resp1.status_code == 201
    tx_id_1 = resp1.json()["id"]

    # Retry with same idempotency key
    resp2 = postgres_client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "999.00", "tipo": "egreso"},
        headers={"Idempotency-Key": "pg-idem-test"},
    )
    assert resp2.status_code == 201
    tx_id_2 = resp2.json()["id"]

    assert tx_id_1 == tx_id_2, "Idempotency should return same transaction"


@pytest.mark.postgres
@postgres_available
def test_postgres_status_change(postgres_client: TestClient) -> None:
    """Verify status change is persisted to Postgres."""
    user_id = str(uuid4())

    resp = postgres_client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "20.00", "tipo": "ingreso"},
    )
    tx_id = resp.json()["id"]

    resp2 = postgres_client.patch(f"/transactions/{tx_id}/status", json={"status": "procesado"})
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "procesado"

    # Verify persisted
    tx = postgres_client.app.state.transaction_repo.get(tx_id)
    assert tx is not None
    assert tx.status.value == "procesado"


@pytest.mark.postgres
@postgres_available
def test_postgres_summary_persisted(postgres_client: TestClient) -> None:
    """Verify summary is persisted to Postgres."""
    resp = postgres_client.post(
        "/assistant/summarize",
        json={"text": "Hello world from Postgres test", "model": "test-model"},
        headers={"X-Request-Id": "pg-req-123"},
    )
    assert resp.status_code == 201
    body = resp.json()

    # Verify persisted
    s = postgres_client.app.state.summary_repo.get(body["id"])
    assert s is not None
    assert s.request_id == "pg-req-123"

