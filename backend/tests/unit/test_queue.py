"""
Unit tests for queue implementations.

Tests cover:
1. InMemoryQueue enqueue/dequeue
2. FIFO ordering
3. Clear operation
"""
from __future__ import annotations

from app.infra.queue import InMemoryQueue


def test_in_memory_queue_enqueue_dequeue() -> None:
    """InMemoryQueue should enqueue and dequeue in FIFO order."""
    queue = InMemoryQueue()

    job_id1 = queue.enqueue("type1", {"key": "value1"})
    job_id2 = queue.enqueue("type2", {"key": "value2"})

    assert queue.pending_count() == 2

    result1 = queue.dequeue()
    assert result1 is not None
    assert result1[0] == job_id1
    assert result1[1] == "type1"
    assert result1[2] == {"key": "value1"}

    result2 = queue.dequeue()
    assert result2 is not None
    assert result2[0] == job_id2

    assert queue.dequeue() is None
    assert queue.pending_count() == 0


def test_in_memory_queue_clear() -> None:
    """InMemoryQueue.clear() should remove all pending jobs."""
    queue = InMemoryQueue()
    queue.enqueue("type", {"x": 1})
    queue.enqueue("type", {"x": 2})

    queue.clear()

    assert queue.pending_count() == 0
    assert queue.dequeue() is None

