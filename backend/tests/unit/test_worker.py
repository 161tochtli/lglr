"""
Unit tests for worker handler.

Tests cover:
1. process_transaction updates status to procesado
2. process_transaction updates status to fallido on failure
3. process_transaction raises on missing transaction
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from app.domain.models import TransactionStatus, TransactionType, create_transaction
from app.repos.in_memory import InMemoryTransactionRepo
from app.worker.handler import process_transaction


def test_worker_handler_updates_status_to_posted() -> None:
    """Worker handler should update status to 'posted' on success."""
    repo = InMemoryTransactionRepo()
    tx = create_transaction(user_id=uuid4(), monto=10, tipo=TransactionType.ingreso)
    repo.add(tx)

    # Process with 0% fail probability
    new_status = process_transaction(
        repo,
        tx.id,
        simulate_work_seconds=0.01,  # Fast for tests
        fail_probability=0.0,
        job_id="test-job",
    )

    assert new_status == TransactionStatus.procesado
    updated = repo.get(tx.id)
    assert updated is not None
    assert updated.status == TransactionStatus.procesado


def test_worker_handler_updates_status_to_failed() -> None:
    """Worker handler should update status to 'failed' when simulated failure."""
    repo = InMemoryTransactionRepo()
    tx = create_transaction(user_id=uuid4(), monto=10, tipo=TransactionType.ingreso)
    repo.add(tx)

    # Process with 100% fail probability
    new_status = process_transaction(
        repo,
        tx.id,
        simulate_work_seconds=0.01,
        fail_probability=1.0,
        job_id="test-job",
    )

    assert new_status == TransactionStatus.fallido
    updated = repo.get(tx.id)
    assert updated is not None
    assert updated.status == TransactionStatus.fallido


def test_worker_handler_raises_on_missing_transaction() -> None:
    """Worker handler should raise KeyError for non-existent transaction."""
    repo = InMemoryTransactionRepo()
    fake_id = uuid4()

    with pytest.raises(KeyError, match="transaction not found"):
        process_transaction(repo, fake_id, simulate_work_seconds=0.01)

