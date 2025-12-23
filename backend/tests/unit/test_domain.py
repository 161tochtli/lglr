"""
Unit tests for domain models, events, and correlation.

Tests cover:
1. Domain models (Transaction, Summary) and their factories
2. Domain events
3. Correlation constants and context variables
"""
from __future__ import annotations

from datetime import timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain import events
from app.domain.correlation import (
    CTX_IDEMPOTENCY_KEY,
    CTX_REQUEST_ID,
    CTX_TRANSACTION_ID,
    IDEMPOTENCY_KEY_HEADER,
    REQUEST_ID_HEADER,
    TRANSACTION_ID_HEADER,
)
from app.domain.models import (
    NewSummary,
    NewTransaction,
    TransactionStatus,
    TransactionType,
    create_transaction,
    with_transaction_status,
)


# ---------------------------------------------------------------------------
# Correlation constants
# ---------------------------------------------------------------------------


def test_correlation_constants_are_stable() -> None:
    assert REQUEST_ID_HEADER == "X-Request-Id"
    assert TRANSACTION_ID_HEADER == "X-Transaction-Id"
    assert IDEMPOTENCY_KEY_HEADER == "Idempotency-Key"
    assert CTX_REQUEST_ID == "request_id"
    assert CTX_TRANSACTION_ID == "transaction_id"
    assert CTX_IDEMPOTENCY_KEY == "idempotency_key"


# ---------------------------------------------------------------------------
# Transaction model
# ---------------------------------------------------------------------------


def test_create_transaction_sets_pending_and_utc_timestamps() -> None:
    user_id = uuid4()
    tx = create_transaction(user_id=user_id, monto=Decimal("10.50"), tipo=TransactionType.ingreso)

    assert tx.user_id == user_id
    assert tx.monto == Decimal("10.50")
    assert tx.tipo == TransactionType.ingreso
    assert tx.status == TransactionStatus.pendiente

    assert tx.created_at.tzinfo == timezone.utc
    assert tx.updated_at.tzinfo == timezone.utc
    assert tx.updated_at == tx.created_at


def test_with_transaction_status_keeps_created_at_and_changes_updated_at() -> None:
    tx = create_transaction(user_id=uuid4(), monto=Decimal("1.00"), tipo=TransactionType.egreso)
    updated = with_transaction_status(tx, new_status=TransactionStatus.procesado)

    assert updated.id == tx.id
    assert updated.status == TransactionStatus.procesado
    assert updated.created_at == tx.created_at
    assert updated.updated_at >= tx.updated_at


@pytest.mark.parametrize("monto", [Decimal("0"), Decimal("-1")])
def test_new_transaction_rejects_non_positive_monto(monto: Decimal) -> None:
    with pytest.raises(ValidationError):
        NewTransaction(user_id=uuid4(), monto=monto, tipo=TransactionType.ingreso)


# ---------------------------------------------------------------------------
# Summary model
# ---------------------------------------------------------------------------


def test_new_summary_rejects_empty_text() -> None:
    with pytest.raises(ValidationError):
        NewSummary(text="   ", model="x")


# ---------------------------------------------------------------------------
# Domain events
# ---------------------------------------------------------------------------


def test_domain_events_have_expected_names_and_payload_shape() -> None:
    tx = create_transaction(user_id=uuid4(), monto=Decimal("2.00"), tipo=TransactionType.ingreso)
    evt = events.transaction_created(tx)

    assert evt.name == "transaction.created"
    assert evt.payload["transaction_id"] == str(tx.id)
    assert evt.payload["user_id"] == str(tx.user_id)
    assert evt.payload["monto"] == str(tx.monto)
    assert evt.payload["tipo"] == tx.tipo.value
    assert evt.payload["status"] == tx.status.value

    evt2 = events.transaction_status_changed(
        transaction_id=str(tx.id),
        old_status=TransactionStatus.pendiente,
        new_status=TransactionStatus.fallido,
    )
    assert evt2.name == "transaction.status_changed"
    assert evt2.payload["transaction_id"] == str(tx.id)
    assert evt2.payload["old_status"] == TransactionStatus.pendiente.value
    assert evt2.payload["new_status"] == TransactionStatus.fallido.value

