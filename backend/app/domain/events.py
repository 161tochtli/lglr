from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from app.domain.models import Summary, Transaction, TransactionStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    name: str
    payload: Mapping[str, Any]
    occurred_at: datetime


def transaction_created(tx: Transaction) -> DomainEvent:
    return DomainEvent(
        name="transaction.created",
        payload={
            "transaction_id": str(tx.id),
            "user_id": str(tx.user_id),
            "monto": str(tx.monto),
            "tipo": tx.tipo.value,
            "status": tx.status.value,
        },
        occurred_at=utcnow(),
    )


def transaction_status_changed(
    *, transaction_id: str, old_status: TransactionStatus, new_status: TransactionStatus
) -> DomainEvent:
    return DomainEvent(
        name="transaction.status_changed",
        payload={
            "transaction_id": transaction_id,
            "old_status": old_status.value,
            "new_status": new_status.value,
        },
        occurred_at=utcnow(),
    )


def assistant_summary_created(s: Summary) -> DomainEvent:
    return DomainEvent(
        name="assistant.summary_created",
        payload={
            "summary_id": str(s.id),
            "model": s.model,
            "request_id": s.request_id,
        },
        occurred_at=utcnow(),
    )


