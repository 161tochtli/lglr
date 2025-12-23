"""
Event bus for publishing domain events to subscribers.

Provides in-memory implementation for simplicity.
Can be replaced with Redis Pub/Sub for distributed systems.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


# Type alias for async event handlers
EventHandler = Callable[[str, dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus(ABC):
    """Abstract base for event bus implementations."""

    @abstractmethod
    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish an event to all subscribers."""
        ...

    @abstractmethod
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        ...

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        ...


@dataclass
class InMemoryEventBus(EventBus):
    """
    In-memory event bus using asyncio.

    Suitable for single-process deployments and testing.
    For multi-process, use Redis Pub/Sub.
    """

    _handlers: dict[str, list[EventHandler]] = field(default_factory=lambda: defaultdict(list))

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish event to all registered handlers."""
        import structlog
        logger = structlog.get_logger(__name__)
        
        handlers = self._handlers.get(event_type, [])
        # Also notify wildcard subscribers
        handlers = handlers + self._handlers.get("*", [])
        
        logger.debug("event_bus.publishing", event_type=event_type, handler_count=len(handlers))

        for handler in handlers:
            try:
                await handler(event_type, payload)
            except Exception as e:
                # Don't let one handler crash others
                logger.exception("event_bus.handler_error", error=str(e))

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe handler to event type. Use '*' for all events."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe handler from event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def clear(self) -> None:
        """Remove all handlers (for testing)."""
        self._handlers.clear()

