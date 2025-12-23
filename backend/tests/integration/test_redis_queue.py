"""
Integration tests with Redis using testcontainers.

These tests automatically spin up a Redis container, run tests against it,
and tear it down. No manual Docker setup required.

Requires:
  - Docker running
  - testcontainers[redis] installed

Skip automatically if Docker is not available.
"""
from __future__ import annotations

import time
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.domain.models import TransactionStatus
from conftest import requires_docker


@requires_docker
class TestRedisQueueWithTestcontainers:
    """Integration tests using Redis via testcontainers."""

    def test_redis_queue_enqueue_dequeue(self, redis_queue) -> None:  # type: ignore[no-untyped-def]
        """Verify RedisQueue works with real Redis."""
        job_id = redis_queue.enqueue("test_job", {"key": "value"})
        assert job_id.startswith("job-")

        result = redis_queue.dequeue(timeout=1)
        assert result is not None
        assert result[1] == "test_job"
        assert result[2] == {"key": "value"}

    def test_redis_queue_fifo_order(self, redis_queue) -> None:  # type: ignore[no-untyped-def]
        """Verify Redis queue maintains FIFO order."""
        redis_queue.enqueue("type", {"order": 1})
        redis_queue.enqueue("type", {"order": 2})
        redis_queue.enqueue("type", {"order": 3})

        r1 = redis_queue.dequeue()
        r2 = redis_queue.dequeue()
        r3 = redis_queue.dequeue()

        assert r1 is not None and r1[2]["order"] == 1
        assert r2 is not None and r2[2]["order"] == 2
        assert r3 is not None and r3[2]["order"] == 3

    def test_redis_queue_timeout_returns_none(self, redis_queue) -> None:  # type: ignore[no-untyped-def]
        """Verify dequeue returns None on empty queue after timeout."""
        redis_queue.clear()
        result = redis_queue.dequeue(timeout=1)
        assert result is None

    def test_async_process_with_redis_updates_status(self, redis_client: TestClient) -> None:
        """Full integration: API → Redis queue → worker → status updated."""
        user_id = str(uuid4())

        # Create transaction
        resp = redis_client.post(
            "/transactions/create",
            json={"user_id": user_id, "monto": "50.00", "tipo": "ingreso"},
        )
        assert resp.status_code == 201
        tx_id_str = resp.json()["id"]
        tx_id = UUID(tx_id_str)

        # Enqueue for async processing
        resp2 = redis_client.post(
            "/transactions/async-process",
            params={"transaction_id": tx_id_str},
        )
        assert resp2.status_code == 202
        assert "job_id" in resp2.json()

        # Wait for worker to process (max 3 seconds)
        for _ in range(30):
            time.sleep(0.1)
            tx = redis_client.app.state.transaction_repo.get(tx_id)
            if tx and tx.status != TransactionStatus.pendiente:
                break

        # Verify status changed
        tx = redis_client.app.state.transaction_repo.get(tx_id)
        assert tx is not None
        assert tx.status in (TransactionStatus.procesado, TransactionStatus.fallido)

    def test_multiple_transactions_processed_via_redis(self, redis_client: TestClient) -> None:
        """Multiple transactions can be processed through Redis queue."""
        tx_ids = []

        # Create and enqueue 3 transactions
        for i in range(3):
            resp = redis_client.post(
                "/transactions/create",
                json={"user_id": str(uuid4()), "monto": f"{10 + i}.00", "tipo": "egreso"},
            )
            tx_id = resp.json()["id"]
            tx_ids.append(UUID(tx_id))

            redis_client.post(
                "/transactions/async-process",
                params={"transaction_id": tx_id},
            )

        # Wait for all to be processed (max 5 seconds)
        for _ in range(50):
            time.sleep(0.1)
            all_processed = all(
                redis_client.app.state.transaction_repo.get(tx_id).status != TransactionStatus.pendiente
                for tx_id in tx_ids
            )
            if all_processed:
                break

        # Verify all were processed
        for tx_id in tx_ids:
            tx = redis_client.app.state.transaction_repo.get(tx_id)
            assert tx is not None
            assert tx.status in (TransactionStatus.procesado, TransactionStatus.fallido)

