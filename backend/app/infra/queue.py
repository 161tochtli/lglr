"""
Queue abstraction for async job processing.

Provides a Protocol for queue clients and implementations:
- InMemoryQueue: for tests (can drain synchronously)
- RedisQueue: for production (requires Redis)
"""
from __future__ import annotations

import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class QueueClient(ABC):
    """Abstract base for queue implementations."""

    @abstractmethod
    def enqueue(self, job_type: str, payload: dict[str, Any]) -> str:
        """Enqueue a job. Returns job_id."""
        ...

    @abstractmethod
    def dequeue(self, timeout: float = 1.0) -> tuple[str, str, dict[str, Any]] | None:
        """
        Dequeue a job (blocking up to timeout).
        Returns (job_id, job_type, payload) or None if no job available.
        """
        ...


@dataclass
class InMemoryQueue(QueueClient):
    """
    In-memory queue for testing.

    Supports synchronous drain() for test isolation.
    """

    _jobs: list[tuple[str, str, dict[str, Any]]] = field(default_factory=list)
    _job_counter: int = 0

    def enqueue(self, job_type: str, payload: dict[str, Any]) -> str:
        self._job_counter += 1
        job_id = f"job-{self._job_counter}"
        self._jobs.append((job_id, job_type, payload))
        return job_id

    def dequeue(self, timeout: float = 1.0) -> tuple[str, str, dict[str, Any]] | None:
        if not self._jobs:
            return None
        return self._jobs.pop(0)

    def pending_count(self) -> int:
        """Number of jobs waiting to be processed."""
        return len(self._jobs)

    def clear(self) -> None:
        """Clear all pending jobs."""
        self._jobs.clear()
        self._job_counter = 0


@dataclass
class RedisQueue(QueueClient):
    """
    Redis-backed queue for production.

    Uses Redis LIST with BRPOP for blocking dequeue.
    """

    redis_url: str
    queue_name: str = "legali:jobs"
    _client: Any = field(default=None, repr=False)
    _job_counter: int = 0

    def __post_init__(self) -> None:
        # Lazy import to avoid requiring redis in tests
        import redis

        self._client = redis.from_url(self.redis_url, decode_responses=True)

    def enqueue(self, job_type: str, payload: dict[str, Any]) -> str:
        self._job_counter += 1
        job_id = f"job-{self._job_counter}-{time.time()}"
        job_data = json.dumps({"job_id": job_id, "job_type": job_type, "payload": payload})
        self._client.lpush(self.queue_name, job_data)
        return job_id

    def dequeue(self, timeout: float = 1.0) -> tuple[str, str, dict[str, Any]] | None:
        result = self._client.brpop(self.queue_name, timeout=int(timeout))
        if result is None:
            return None
        _, job_data = result
        parsed = json.loads(job_data)
        return parsed["job_id"], parsed["job_type"], parsed["payload"]

    def clear(self) -> None:
        """Clear all pending jobs."""
        self._client.delete(self.queue_name)

