"""
Worker handler for processing async jobs.

The handler is a pure function that:
1. Receives a transaction_id
2. Simulates work (sleep)
3. Updates status to 'posted' (success) or 'failed' (error)
4. Logs the event

This design allows testing without a queue.
"""
import random
import time
from uuid import UUID

import structlog

from app.domain import events
from app.domain.models import TransactionStatus
from app.infra.event_log import get_event_log
from app.repos.ports import TransactionRepo

logger = structlog.get_logger(__name__)


def process_transaction(
    tx_repo: TransactionRepo,
    transaction_id: UUID,
    *,
    simulate_work_seconds: float = 1.0,
    fail_probability: float = 0.1,
    job_id: str | None = None,
) -> TransactionStatus:
    """
    Process a transaction asynchronously.

    Args:
        tx_repo: Repository for transaction persistence.
        transaction_id: The transaction to process.
        simulate_work_seconds: How long to simulate work (default 1s).
        fail_probability: Chance of simulated failure (0.0 to 1.0).
        job_id: Optional job ID for logging correlation.

    Returns:
        The new status after processing.

    Raises:
        KeyError: If transaction not found.
    """
    log = logger.bind(transaction_id=str(transaction_id), job_id=job_id or "-")

    # Get current transaction
    tx = tx_repo.get(transaction_id)
    if tx is None:
        log.error("worker.transaction_not_found")
        raise KeyError(f"transaction not found: {transaction_id}")

    old_status = tx.status
    log.info("worker.processing_started", old_status=old_status.value)

    # Log to event_log for frontend viewer
    get_event_log().append(
        "worker.processing_started",
        service="worker",
        request_id=job_id or "-",
        transaction_id=str(transaction_id),
        job_id=job_id,
        old_status=old_status.value,
    )

    # Simulate work
    start = time.monotonic()
    time.sleep(simulate_work_seconds)
    duration_ms = int((time.monotonic() - start) * 1000)

    # Determine outcome (simulate random failures)
    if random.random() < fail_probability:
        new_status = TransactionStatus.fallido
    else:
        new_status = TransactionStatus.procesado

    # Update status
    updated = tx_repo.update_status(transaction_id, new_status)

    # Log event
    evt = events.transaction_status_changed(
        transaction_id=str(transaction_id),
        old_status=old_status,
        new_status=new_status,
    )
    log.info(
        evt.name,
        old_status=old_status.value,
        new_status=new_status.value,
        duration_ms=duration_ms,
    )

    # Log to event_log for frontend viewer
    get_event_log().append(
        evt.name,
        service="worker",
        request_id=job_id or "-",
        transaction_id=str(transaction_id),
        job_id=job_id,
        old_status=old_status.value,
        new_status=new_status.value,
        duration_ms=duration_ms,
    )

    return updated.status

