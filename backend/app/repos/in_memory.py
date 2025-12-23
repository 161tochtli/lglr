from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.domain.models import (
    Summary,
    Transaction,
    TransactionStatus,
    with_transaction_status,
)


@dataclass
class InMemoryTransactionRepo:
    _items: dict[UUID, Transaction] = field(default_factory=dict)

    def clear(self) -> None:
        self._items.clear()

    def add(self, tx: Transaction) -> None:
        self._items[tx.id] = tx

    def get(self, tx_id: UUID) -> Transaction | None:
        return self._items.get(tx_id)

    def update_status(self, tx_id: UUID, new_status: TransactionStatus) -> Transaction:
        tx = self._items[tx_id]
        updated = with_transaction_status(tx, new_status=new_status)
        self._items[tx_id] = updated
        return updated

    def list_all(self, limit: int = 50, offset: int = 0) -> list[Transaction]:
        """Return transactions sorted by created_at descending."""
        items = sorted(self._items.values(), key=lambda t: t.created_at, reverse=True)
        return items[offset : offset + limit]


@dataclass
class InMemorySummaryRepo:
    _items: dict[UUID, Summary] = field(default_factory=dict)

    def clear(self) -> None:
        self._items.clear()

    def add(self, s: Summary) -> None:
        self._items[s.id] = s

    def get(self, summary_id: UUID) -> Summary | None:
        return self._items.get(summary_id)


@dataclass
class InMemoryIdempotencyStore:
    """
    Minimal idempotency store.

    Maps idempotency_key -> stable result payload (so retries return same outcome).
    """

    _items: dict[str, Any] = field(default_factory=dict)

    def clear(self) -> None:
        self._items.clear()

    def get(self, key: str) -> Any | None:
        return self._items.get(key)

    def put(self, key: str, value: Any) -> None:
        self._items[key] = value


