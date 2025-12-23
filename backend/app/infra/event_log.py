"""
In-memory event log for frontend log viewer.

Stores recent domain events and exposes them via API.
Events are grouped by correlation_id (request_id) for easy timeline viewing.
"""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any


@dataclass(frozen=True, slots=True)
class LogEntry:
    """A single log entry with all relevant metadata."""
    
    timestamp: datetime
    level: str
    service: str
    event: str
    request_id: str
    transaction_id: str | None = None
    job_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "service": self.service,
            "event": self.event,
            "request_id": self.request_id,
            "transaction_id": self.transaction_id,
            "job_id": self.job_id,
            **self.payload,
        }


class EventLog:
    """
    Thread-safe in-memory log storage.
    
    Keeps last N entries and provides grouping by correlation_id.
    """
    
    def __init__(self, max_entries: int = 500) -> None:
        self._entries: deque[LogEntry] = deque(maxlen=max_entries)
        self._lock = Lock()

    def append(
        self,
        event: str,
        *,
        level: str = "INFO",
        service: str = "api",
        request_id: str = "-",
        transaction_id: str | None = None,
        job_id: str | None = None,
        **payload: Any,
    ) -> LogEntry:
        """Add a new log entry."""
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc),
            level=level,
            service=service,
            event=event,
            request_id=request_id,
            transaction_id=transaction_id,
            job_id=job_id,
            payload=payload,
        )
        with self._lock:
            self._entries.append(entry)
        return entry

    def get_all(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get most recent entries as dicts, newest first."""
        with self._lock:
            entries = list(self._entries)
        return [e.to_dict() for e in reversed(entries)][:limit]

    def get_by_request_id(self, request_id: str) -> list[dict[str, Any]]:
        """Get all entries for a specific request_id."""
        with self._lock:
            entries = [e for e in self._entries if e.request_id == request_id]
        return [e.to_dict() for e in entries]

    def get_by_transaction_id(self, transaction_id: str) -> list[dict[str, Any]]:
        """Get all entries for a specific transaction_id."""
        with self._lock:
            entries = [e for e in self._entries if e.transaction_id == transaction_id]
        return [e.to_dict() for e in entries]

    def get_grouped_by_correlation(self, limit: int = 50) -> dict[str, list[dict[str, Any]]]:
        """
        Get entries grouped by request_id (correlation_id).
        
        Returns dict mapping request_id -> list of events in chronological order.
        Limited to the most recent `limit` correlation groups.
        """
        with self._lock:
            entries = list(self._entries)
        
        # Group by request_id
        groups: dict[str, list[LogEntry]] = {}
        for entry in entries:
            if entry.request_id not in groups:
                groups[entry.request_id] = []
            groups[entry.request_id].append(entry)
        
        # Sort groups by the timestamp of their first event (most recent first)
        sorted_groups = sorted(
            groups.items(),
            key=lambda kv: kv[1][0].timestamp if kv[1] else datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )[:limit]
        
        # Convert to dict of dicts
        return {
            request_id: [e.to_dict() for e in events]
            for request_id, events in sorted_groups
        }

    def clear(self) -> None:
        """Clear all entries (for testing)."""
        with self._lock:
            self._entries.clear()


# Global singleton instance
_event_log: EventLog | None = None


def get_event_log() -> EventLog:
    """Get or create the global event log."""
    global _event_log
    if _event_log is None:
        _event_log = EventLog()
    return _event_log

