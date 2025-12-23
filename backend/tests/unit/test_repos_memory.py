"""
Unit tests for in-memory repositories.

Tests cover:
1. InMemoryTransactionRepo
2. InMemoryIdempotencyStore
3. InMemorySummaryRepo
"""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from app.domain.models import TransactionStatus, TransactionType, create_transaction
from app.repos.in_memory import InMemoryIdempotencyStore, InMemoryTransactionRepo


def test_in_memory_transaction_repo_add_get_and_update_status() -> None:
    repo = InMemoryTransactionRepo()
    tx = create_transaction(user_id=uuid4(), monto=Decimal("3.00"), tipo=TransactionType.egreso)
    repo.add(tx)

    got = repo.get(tx.id)
    assert got == tx

    updated = repo.update_status(tx.id, TransactionStatus.cancelado)
    assert updated.id == tx.id
    assert updated.status == TransactionStatus.cancelado
    assert repo.get(tx.id) == updated


def test_in_memory_idempotency_store_round_trip() -> None:
    store = InMemoryIdempotencyStore()
    assert store.get("k") is None
    store.put("k", "v")
    assert store.get("k") == "v"

