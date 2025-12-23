from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TransactionType(StrEnum):
    ingreso = "ingreso"
    egreso = "egreso"


class TransactionStatus(StrEnum):
    pendiente = "pendiente"
    procesado = "procesado"
    fallido = "fallido"
    cancelado = "cancelado"


class Transaction(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    user_id: UUID
    monto: Decimal = Field(gt=Decimal("0"))
    tipo: TransactionType
    status: TransactionStatus
    created_at: datetime
    updated_at: datetime


class NewTransaction(BaseModel):
    user_id: UUID
    monto: Decimal = Field(gt=Decimal("0"))
    tipo: TransactionType


class TransactionStatusChange(BaseModel):
    status: TransactionStatus


class Summary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    text: str = Field(min_length=1)
    summary: str
    created_at: datetime
    model: str | None = None
    request_id: str | None = None


class NewSummary(BaseModel):
    text: str = Field(min_length=1)
    model: str | None = None

    @field_validator("text")
    @classmethod
    def normalize_text(cls, v: str) -> str:
        # Normalize whitespace and reject blank content.
        trimmed = " ".join(v.strip().split())
        if not trimmed:
            raise ValueError("text must not be blank")
        return trimmed


def create_transaction(*, user_id: UUID, monto: Decimal, tipo: TransactionType) -> Transaction:
    now = utcnow()
    return Transaction(
        id=uuid4(),
        user_id=user_id,
        monto=monto,
        tipo=tipo,
        status=TransactionStatus.pendiente,
        created_at=now,
        updated_at=now,
    )


def with_transaction_status(
    tx: Transaction, *, new_status: TransactionStatus
) -> Transaction:
    return Transaction(
        id=tx.id,
        user_id=tx.user_id,
        monto=tx.monto,
        tipo=tx.tipo,
        status=new_status,
        created_at=tx.created_at,
        updated_at=utcnow(),
    )


def create_summary(
    *, text: str, summary: str, model: str | None, request_id: str | None
) -> Summary:
    return Summary(
        id=uuid4(),
        text=text,
        summary=summary,
        created_at=utcnow(),
        model=model,
        request_id=request_id,
    )


