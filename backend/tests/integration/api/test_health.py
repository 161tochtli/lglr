"""
Integration tests for health endpoint.
"""
from __future__ import annotations


def test_health_has_request_id_header(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert resp.headers.get("X-Request-Id")


def test_health_respects_client_request_id(client) -> None:  # type: ignore[no-untyped-def]
    resp = client.get("/health", headers={"X-Request-Id": "req-123"})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-Id") == "req-123"

