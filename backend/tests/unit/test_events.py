"""
Unit tests for event bus implementations.

Tests cover:
1. InMemoryEventBus publish/subscribe
2. Wildcard subscribers
3. Unsubscribe
"""
from __future__ import annotations

import pytest

from app.infra.events import InMemoryEventBus


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe() -> None:
    """EventBus should deliver events to subscribers."""
    bus = InMemoryEventBus()
    received = []

    async def handler(event_type: str, payload: dict) -> None:
        received.append((event_type, payload))

    bus.subscribe("test.event", handler)
    await bus.publish("test.event", {"key": "value"})

    assert len(received) == 1
    assert received[0] == ("test.event", {"key": "value"})


@pytest.mark.asyncio
async def test_event_bus_wildcard_subscriber() -> None:
    """Wildcard '*' subscriber should receive all events."""
    bus = InMemoryEventBus()
    received = []

    async def handler(event_type: str, payload: dict) -> None:
        received.append(event_type)

    bus.subscribe("*", handler)
    await bus.publish("event.one", {})
    await bus.publish("event.two", {})

    assert received == ["event.one", "event.two"]


@pytest.mark.asyncio
async def test_event_bus_unsubscribe() -> None:
    """Unsubscribed handler should not receive events."""
    bus = InMemoryEventBus()
    received = []

    async def handler(event_type: str, payload: dict) -> None:
        received.append(event_type)

    bus.subscribe("test", handler)
    await bus.publish("test", {})
    assert len(received) == 1

    bus.unsubscribe("test", handler)
    await bus.publish("test", {})
    assert len(received) == 1  # Still 1, not 2

