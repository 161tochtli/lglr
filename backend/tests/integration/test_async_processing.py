"""
Integration tests for async processing (queue + worker).

Tests cover:
1. Endpoint POST /transactions/async-process
2. Integration: enqueue → worker processes → status updated
"""
from __future__ import annotations

import time
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.domain.models import TransactionStatus
from app.infra.queue import InMemoryQueue
from app.main import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def async_client():
    """Client with worker disabled (for endpoint-only tests)."""
    app = create_app(configure_logs=False, persistence="memory", run_worker=False)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def integration_app():
    """App with worker enabled for integration tests."""
    queue = InMemoryQueue()
    app = create_app(
        configure_logs=False,
        persistence="memory",
        queue=queue,
        run_worker=True,
    )
    return app, queue


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


def test_async_process_returns_202_and_job_id(async_client: TestClient) -> None:
    """Endpoint should return 202 Accepted with job_id."""
    user_id = str(uuid4())

    # Create transaction first
    resp = async_client.post(
        "/transactions/create",
        json={"user_id": user_id, "monto": "10.00", "tipo": "ingreso"},
    )
    tx_id = resp.json()["id"]

    # Enqueue for processing
    resp2 = async_client.post(
        "/transactions/async-process",
        params={"transaction_id": tx_id},
    )

    assert resp2.status_code == 202
    body = resp2.json()
    assert "job_id" in body
    assert body["transaction_id"] == tx_id
    assert body["status"] == "enqueued"


def test_async_process_returns_404_for_missing_transaction(async_client: TestClient) -> None:
    """Endpoint should return 404 for non-existent transaction."""
    fake_id = str(uuid4())

    resp = async_client.post(
        "/transactions/async-process",
        params={"transaction_id": fake_id},
    )

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Full integration: enqueue → worker → status updated
# ---------------------------------------------------------------------------


def test_integration_async_process_updates_status(integration_app) -> None:
    """Full integration: enqueue → worker processes → status updated."""
    app, queue = integration_app

    with TestClient(app) as client:
        user_id = str(uuid4())

        # Create transaction
        resp = client.post(
            "/transactions/create",
            json={"user_id": user_id, "monto": "25.00", "tipo": "egreso"},
        )
        tx_id_str = resp.json()["id"]
        tx_id = UUID(tx_id_str)
        assert resp.json()["status"] == "pendiente"

        # Enqueue for processing
        resp2 = client.post(
            "/transactions/async-process",
            params={"transaction_id": tx_id_str},
        )
        assert resp2.status_code == 202

        # Wait for worker to process (max 3 seconds)
        for _ in range(30):
            time.sleep(0.1)
            tx = app.state.transaction_repo.get(tx_id)
            if tx and tx.status != TransactionStatus.pendiente:
                break

        # Verify status changed
        tx = app.state.transaction_repo.get(tx_id)
        assert tx is not None
        assert tx.status in (TransactionStatus.procesado, TransactionStatus.fallido)

