"""
Unit tests for WebSocket ConnectionManager.

Tests cover:
1. Connection tracking
2. Connect/disconnect
"""
from __future__ import annotations

import pytest

from app.api.websocket import ConnectionManager


@pytest.mark.asyncio
async def test_connection_manager_tracks_connections() -> None:
    """ConnectionManager should track connected clients."""
    manager = ConnectionManager()
    assert manager.connection_count == 0

    # We can't easily test with real WebSocket, but we can test the count logic
    # by directly manipulating the internal set (for unit testing purposes)
    class FakeWebSocket:
        async def accept(self) -> None:
            pass

        async def send_text(self, data: str) -> None:
            pass

    ws = FakeWebSocket()
    await manager.connect(ws)  # type: ignore
    assert manager.connection_count == 1

    await manager.disconnect(ws)  # type: ignore
    assert manager.connection_count == 0

