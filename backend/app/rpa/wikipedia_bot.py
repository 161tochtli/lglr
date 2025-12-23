"""
Wikipedia RPA bot using httpx (lightweight HTTP client).

Automates:
1. Search Wikipedia for a term
2. Extract first paragraph
3. Call /assistant/summarize API

Can be run as a standalone script or imported as a module.

Note: Uses httpx instead of Playwright for faster, lighter scraping.
Wikipedia serves static HTML so no JavaScript rendering is needed.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx
import structlog

from app.rpa.extractor import ExtractedContent, WikipediaExtractor

logger = structlog.get_logger(__name__)


@dataclass
class WikipediaBotConfig:
    """Configuration for Wikipedia bot."""

    api_base_url: str = "http://localhost:8000"
    wikipedia_url: str = "https://es.wikipedia.org"
    timeout_seconds: float = 30.0
    # Compliant User-Agent per Wikipedia policy: https://meta.wikimedia.org/wiki/User-Agent_policy
    user_agent: str = "LglrBot/1.0 (https://github.com/legalario; educational project) httpx/0.27"


@dataclass
class SummarizeResult:
    """Result of the full RPA flow."""

    search_term: str
    wikipedia_title: str
    wikipedia_url: str
    original_paragraph: str
    summary: str
    summary_id: str


@dataclass
class WikipediaBot:
    """
    RPA bot for Wikipedia → Summarize flow.

    Uses httpx for HTTP requests (no browser needed) and beautifulsoup4 for parsing.
    Much faster and lighter than Playwright (~5MB vs ~400MB).
    """

    config: WikipediaBotConfig = field(default_factory=WikipediaBotConfig)
    extractor: WikipediaExtractor = field(default_factory=WikipediaExtractor)

    async def search_and_summarize(self, search_term: str) -> SummarizeResult:
        """
        Full RPA flow:
        1. Search Wikipedia
        2. Extract first paragraph
        3. Call summarize API

        Args:
            search_term: Term to search on Wikipedia.

        Returns:
            SummarizeResult with all extracted and generated content.
        """
        logger.info("rpa.started", search_term=search_term)

        # Step 1: Search Wikipedia and extract content
        content = await self._search_wikipedia(search_term)

        # Step 2: Call summarize API
        summary_response = await self._call_summarize_api(content.first_paragraph)

        result = SummarizeResult(
            search_term=search_term,
            wikipedia_title=content.title,
            wikipedia_url=content.url or "",
            original_paragraph=content.first_paragraph,
            summary=summary_response["summary"],
            summary_id=summary_response["id"],
        )

        logger.info(
            "rpa.completed",
            search_term=search_term,
            title=result.wikipedia_title,
            summary_id=result.summary_id,
        )

        return result

    async def _search_wikipedia(self, search_term: str) -> ExtractedContent:
        """Search Wikipedia and extract content using Wikipedia API + httpx."""
        headers = {"User-Agent": self.config.user_agent}

        async with httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            headers=headers,
            follow_redirects=True,
        ) as client:
            # Use Wikipedia API to search (more reliable than web scraping)
            api_url = f"{self.config.wikipedia_url}/w/api.php"
            params = {
                "action": "opensearch",
                "search": search_term,
                "limit": "1",
                "namespace": "0",
                "format": "json",
            }

            logger.info("rpa.api_search", search_term=search_term)
            response = await client.get(api_url, params=params)
            response.raise_for_status()

            data = response.json()
            # OpenSearch returns: [query, [titles], [descriptions], [urls]]
            if len(data) < 4 or not data[3]:
                raise ValueError(f"No results found for: {search_term}")

            article_url = data[3][0]  # First result URL
            article_title = data[1][0] if data[1] else search_term

            logger.info("rpa.fetching", url=article_url, title=article_title)

            # Fetch the article page
            response = await client.get(article_url)
            response.raise_for_status()

            return self.extractor.extract(response.text, url=str(response.url))

    async def _call_summarize_api(self, text: str) -> dict:
        """Call the /assistant/summarize API."""
        url = f"{self.config.api_base_url}/assistant/summarize"

        logger.info("rpa.calling_api", url=url, text_length=len(text))

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={"text": text},
            )
            response.raise_for_status()
            return response.json()


async def run_bot(search_term: str, config: WikipediaBotConfig | None = None) -> SummarizeResult:
    """
    Convenience function to run the bot.

    Args:
        search_term: Term to search on Wikipedia.
        config: Optional configuration override.

    Returns:
        SummarizeResult with extracted and summarized content.
    """
    bot = WikipediaBot(config=config or WikipediaBotConfig())
    return await bot.search_and_summarize(search_term)


def main() -> None:
    """CLI entry point for running the bot."""
    import sys

    # Fix Windows console encoding for Unicode
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

    if len(sys.argv) < 2:
        print("Usage: python -m app.rpa.wikipedia_bot <search_term>")
        print("Example: python -m app.rpa.wikipedia_bot 'Albert Einstein'")
        sys.exit(1)

    search_term = " ".join(sys.argv[1:])

    # Configure logging for CLI
    from app.infra.logging import configure_logging

    configure_logging(service_name="rpa", json_output=False)

    result = asyncio.run(run_bot(search_term))

    print("\n" + "=" * 60)
    print(f"Search term: {result.search_term}")
    print(f"Wikipedia title: {result.wikipedia_title}")
    print(f"Wikipedia URL: {result.wikipedia_url}")
    print("=" * 60)
    print(f"\nOriginal paragraph:\n{result.original_paragraph[:500]}...")
    print("=" * 60)
    print(f"\nSummary (ID: {result.summary_id}):\n{result.summary}")
    print("=" * 60)


if __name__ == "__main__":
    main()
