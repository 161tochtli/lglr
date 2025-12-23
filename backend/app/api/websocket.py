"""
WebSocket endpoint for real-time transaction updates.

Clients connect to /transactions/stream and receive notifications
when transaction status changes.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.infra.events import EventBus

router = APIRouter(tags=["websocket"])
logger = structlog.get_logger(__name__)


@dataclass
class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages.

    Thread-safe for use with asyncio.
    """

    _connections: set[WebSocket] = field(default_factory=set)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info("ws.connected", clients=len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self._connections.discard(websocket)
        logger.info("ws.disconnected", clients=len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send message to all connected clients."""
        async with self._lock:
            connections = list(self._connections)

        if not connections:
            return

        json_message = json.dumps(message)
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_text(json_message)
            except Exception:
                disconnected.append(websocket)

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self._connections.discard(ws)

        logger.info("ws.broadcast", event_type=message.get("event"), clients=len(connections))

    @property
    def connection_count(self) -> int:
        """Number of active connections."""
        return len(self._connections)


# Global connection manager (will be set from app.state)
def _get_manager(websocket: WebSocket) -> ConnectionManager:
    return websocket.app.state.connection_manager


def _get_event_bus(websocket: WebSocket) -> EventBus:
    return websocket.app.state.event_bus


@router.websocket("/transactions/stream")
async def transaction_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time transaction updates.

    Clients receive JSON messages when transaction status changes:
    {
        "event": "transaction.status_changed",
        "transaction_id": "...",
        "old_status": "pendiente",
        "new_status": "procesado",
        "timestamp": "..."
    }
    """
    manager = _get_manager(websocket)
    await manager.connect(websocket)

    try:
        # Keep connection alive, listen for client messages (ping/pong)
        while True:
            # Wait for any message from client (keeps connection alive)
            # Client can send "ping" and we respond with "pong"
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send keepalive
                try:
                    await websocket.send_text(json.dumps({"type": "keepalive"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)


async def create_event_handler(manager: ConnectionManager):
    """
    Create an event handler that broadcasts to WebSocket clients.

    Returns a coroutine that can be registered with EventBus.
    """

    async def handler(event_type: str, payload: dict[str, Any]) -> None:
        message = {"event": event_type, **payload}
        await manager.broadcast(message)

    return handler

