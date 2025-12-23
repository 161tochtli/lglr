from __future__ import annotations

from uuid import UUID

import structlog
from asgi_correlation_id import correlation_id
from fastapi import APIRouter, Header, HTTPException, Request, Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.domain import events
from app.domain.correlation import (
    IDEMPOTENCY_KEY_HEADER,
    TRANSACTION_ID_HEADER,
)
from app.domain.models import NewTransaction, Transaction, TransactionStatusChange, create_transaction
from app.infra.event_log import get_event_log
from app.infra.queue import QueueClient
from app.repos.ports import IdempotencyStore, TransactionRepo

router = APIRouter(tags=["transactions"])
logger = structlog.get_logger(__name__)


def _repos(request: Request) -> tuple[TransactionRepo, IdempotencyStore]:
    return request.app.state.transaction_repo, request.app.state.idempotency_store


def _queue(request: Request) -> QueueClient:
    return request.app.state.queue


@router.get("/transactions", response_model=list[Transaction])
def list_transactions_endpoint(
    request: Request,
    limit: int = 50,
    offset: int = 0,
) -> list[Transaction]:
    """List all transactions, ordered by created_at descending."""
    tx_repo, _ = _repos(request)
    return tx_repo.list_all(limit=limit, offset=offset)


@router.post("/transactions/create", response_model=Transaction, status_code=201)
def create_transaction_endpoint(
    request: Request,
    response: Response,
    body: NewTransaction,
    idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_KEY_HEADER),
) -> Transaction:
    tx_repo, idem = _repos(request)

    if idempotency_key:
        existing = idem.get(idempotency_key)
        if isinstance(existing, str):
            tx = tx_repo.get(UUID(existing))
            if tx is not None:
                response.headers[IDEMPOTENCY_KEY_HEADER] = idempotency_key
                response.headers[TRANSACTION_ID_HEADER] = str(tx.id)
                return tx

    tx = create_transaction(user_id=body.user_id, monto=body.monto, tipo=body.tipo)
    tx_repo.add(tx)

    if idempotency_key:
        idem.put(idempotency_key, str(tx.id))
        response.headers[IDEMPOTENCY_KEY_HEADER] = idempotency_key

    response.headers[TRANSACTION_ID_HEADER] = str(tx.id)

    # Bind correlation ids for consistent logging.
    request_id = correlation_id.get() or "-"
    try:
        bind_contextvars(
            transaction_id=str(tx.id),
            idempotency_key=idempotency_key,
            request_id=request_id,
        )
        evt = events.transaction_created(tx)
        logger.info(evt.name, **evt.payload)

        # Also log to event_log for frontend viewer
        get_event_log().append(
            evt.name,
            service="api",
            request_id=request_id,
            transaction_id=str(tx.id),
            user_id=str(tx.user_id),
            monto=str(tx.monto),
            tipo=tx.tipo.value,
            status=tx.status.value,
        )
    finally:
        clear_contextvars()

    return tx


@router.patch("/transactions/{transaction_id}/status", response_model=Transaction)
def change_transaction_status_endpoint(
    request: Request,
    response: Response,
    transaction_id: UUID,
    body: TransactionStatusChange,
) -> Transaction:
    tx_repo, _ = _repos(request)
    existing = tx_repo.get(transaction_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="transaction not found")

    updated = tx_repo.update_status(transaction_id, body.status)
    response.headers[TRANSACTION_ID_HEADER] = str(updated.id)

    try:
        bind_contextvars(
            transaction_id=str(updated.id),
            request_id=correlation_id.get() or "-",
        )
        evt = events.transaction_status_changed(
            transaction_id=str(updated.id),
            old_status=existing.status,
            new_status=updated.status,
        )
        logger.info(evt.name, **evt.payload)
    finally:
        clear_contextvars()

    return updated


@router.post("/transactions/async-process", status_code=202)
def async_process_transaction_endpoint(
    request: Request,
    response: Response,
    transaction_id: UUID,
) -> dict:
    """
    Enqueue a transaction for async processing.

    The worker will:
    1. Simulate work (sleep)
    2. Update status to 'posted' or 'failed'

    Returns immediately with job_id.
    """
    tx_repo, _ = _repos(request)
    queue = _queue(request)

    # Verify transaction exists
    tx = tx_repo.get(transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="transaction not found")

    # Enqueue for processing
    job_id = queue.enqueue("process_transaction", {"transaction_id": str(transaction_id)})

    response.headers[TRANSACTION_ID_HEADER] = str(transaction_id)

    request_id = correlation_id.get() or "-"
    try:
        bind_contextvars(
            transaction_id=str(transaction_id),
            job_id=job_id,
            request_id=request_id,
        )
        logger.info(
            "transaction.enqueued",
            transaction_id=str(transaction_id),
            job_id=job_id,
        )

        # Log to event_log for frontend viewer
        get_event_log().append(
            "transaction.enqueued",
            service="api",
            request_id=request_id,
            transaction_id=str(transaction_id),
            job_id=job_id,
        )
    finally:
        clear_contextvars()

    return {"job_id": job_id, "transaction_id": str(transaction_id), "status": "enqueued"}


