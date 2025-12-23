from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.domain.models import Summary, Transaction, TransactionStatus


class TransactionRepo(Protocol):
    def add(self, tx: Transaction) -> None: ...

    def get(self, tx_id: UUID) -> Transaction | None: ...

    def update_status(self, tx_id: UUID, new_status: TransactionStatus) -> Transaction: ...

    def list_all(self, limit: int = 50, offset: int = 0) -> list[Transaction]: ...


class SummaryRepo(Protocol):
    def add(self, s: Summary) -> None: ...

    def get(self, summary_id: UUID) -> Summary | None: ...


class IdempotencyStore(Protocol):
    def get(self, key: str) -> Any | None: ...

    def put(self, key: str, value: Any) -> None: ...



