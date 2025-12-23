"""
API endpoint for viewing event logs.

Provides read-only access to the in-memory event log
for the frontend log viewer.
"""
from typing import Any

from fastapi import APIRouter, Query

from app.infra.event_log import get_event_log

router = APIRouter(tags=["logs"])


@router.get("/logs")
def list_logs(
    limit: int = Query(default=100, ge=1, le=500),
) -> list[dict[str, Any]]:
    """Get recent log entries, newest first."""
    return get_event_log().get_all(limit=limit)


@router.get("/logs/grouped")
def list_logs_grouped(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, list[dict[str, Any]]]:
    """
    Get log entries grouped by correlation_id (request_id).
    
    Returns a dict where keys are request_ids and values are
    arrays of events in chronological order.
    """
    return get_event_log().get_grouped_by_correlation(limit=limit)


@router.get("/logs/transaction/{transaction_id}")
def get_transaction_logs(
    transaction_id: str,
) -> list[dict[str, Any]]:
    """Get all log entries for a specific transaction."""
    return get_event_log().get_by_transaction_id(transaction_id)


@router.get("/logs/request/{request_id}")
def get_request_logs(
    request_id: str,
) -> list[dict[str, Any]]:
    """Get all log entries for a specific request/correlation."""
    return get_event_log().get_by_request_id(request_id)

