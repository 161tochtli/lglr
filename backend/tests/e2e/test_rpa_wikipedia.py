"""
End-to-end tests for RPA (Wikipedia scraper + summarize).

These tests make real network requests - run only when needed.

Skip with: pytest -m "not slow"
"""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from uuid import uuid4

import pytest


# ---------------------------------------------------------------------------
# Real Wikipedia extraction (requires network + httpx)
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.e2e
async def test_real_wikipedia_extraction_with_httpx() -> None:
    """
    Smoke test: Actually fetch Wikipedia page and extract content using httpx.

    This test makes real network requests - run only when needed.
    """
    import httpx

    from app.rpa.extractor import WikipediaExtractor

    extractor = WikipediaExtractor()

    async with httpx.AsyncClient(
        timeout=30.0,
        headers={"User-Agent": "LglrBot/1.0 (Test)"},
        follow_redirects=True,
    ) as client:
        # Fetch a known Wikipedia page
        url = "https://es.wikipedia.org/wiki/Python_(lenguaje_de_programaci%C3%B3n)"
        response = await client.get(url)
        response.raise_for_status()

        result = extractor.extract(response.text, url=str(response.url))

        # Basic assertions
        assert result.title  # Has a title
        assert "Python" in result.title
        assert len(result.first_paragraph) > 100  # Has substantial content
        assert "programación" in result.first_paragraph.lower()


@pytest.mark.slow
@pytest.mark.e2e
async def test_real_wikipedia_bot_search() -> None:
    """
    Test the Wikipedia bot search functionality with real network.
    """
    from app.rpa.wikipedia_bot import WikipediaBot, WikipediaBotConfig

    config = WikipediaBotConfig(
        api_base_url="http://localhost:8000",  # Won't be called in this test
    )
    bot = WikipediaBot(config=config)

    # Test the search method directly
    content = await bot._search_wikipedia("Albert Einstein")

    assert content.title
    assert "Einstein" in content.title
    assert len(content.first_paragraph) > 100
    assert content.url
    assert "wikipedia.org" in content.url


# ---------------------------------------------------------------------------
# Full RPA flow with mock API
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.e2e
async def test_full_rpa_flow_with_mock_api() -> None:
    """
    Full RPA flow test with mocked API.

    Tests the complete flow but uses a mock server instead of real API.
    """
    from app.rpa.wikipedia_bot import WikipediaBot, WikipediaBotConfig

    # Create a simple mock server
    class MockHandler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data)

            response = {
                "id": str(uuid4()),
                "text": body["text"],
                "summary": f"[Mock summary] {body['text'][:50]}...",
                "model": None,
                "request_id": None,
                "created_at": "2024-01-01T00:00:00Z",
            }

            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        def log_message(self, format, *args) -> None:  # type: ignore[no-untyped-def]
            pass  # Suppress logs

    # Start mock server
    server = HTTPServer(("localhost", 0), MockHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        config = WikipediaBotConfig(
            api_base_url=f"http://localhost:{port}",
        )

        bot = WikipediaBot(config=config)
        result = await bot.search_and_summarize("Python programación")

        # Assertions
        assert result.search_term == "Python programación"
        assert result.wikipedia_title  # Should have extracted title
        assert result.original_paragraph  # Should have extracted content
        assert "[Mock summary]" in result.summary  # Should have called mock API
        assert result.summary_id  # Should have summary ID

    finally:
        server.shutdown()
