"""
Wikipedia HTML extractor.

Parses Wikipedia HTML to extract the first paragraph.
Designed for testability with local HTML fixtures.
"""
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ExtractedContent:
    """Result of extracting content from a Wikipedia page."""

    title: str
    first_paragraph: str
    url: str | None = None


class WikipediaExtractor:
    """
    Extracts content from Wikipedia HTML.

    Designed as a pure function-like class for easy testing
    with local HTML fixtures.
    """

    def extract(self, html: str, url: str | None = None) -> ExtractedContent:
        """
        Extract title and first paragraph from Wikipedia HTML.

        Args:
            html: Raw HTML content from Wikipedia page.
            url: Optional URL for reference.

        Returns:
            ExtractedContent with title and first paragraph.

        Raises:
            ExtractionError: If required content cannot be found.
        """
        soup = BeautifulSoup(html, "html.parser")

        # Extract title
        title = self._extract_title(soup)

        # Extract first paragraph
        first_paragraph = self._extract_first_paragraph(soup)

        logger.info(
            "wikipedia.extracted",
            title=title,
            paragraph_length=len(first_paragraph),
            url=url,
        )

        return ExtractedContent(
            title=title,
            first_paragraph=first_paragraph,
            url=url,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title from Wikipedia HTML."""
        # Try <h1 id="firstHeading"> first (Wikipedia standard)
        heading = soup.find("h1", {"id": "firstHeading"})
        if heading:
            return heading.get_text(strip=True)

        # Fallback to <title> tag
        title_tag = soup.find("title")
        if title_tag:
            text = title_tag.get_text(strip=True)
            # Remove " - Wikipedia" suffix
            if " - Wikipedia" in text:
                text = text.split(" - Wikipedia")[0]
            return text

        raise ExtractionError("Could not find page title")

    def _extract_first_paragraph(self, soup: BeautifulSoup) -> str:
        """
        Extract first meaningful paragraph from Wikipedia HTML.

        Wikipedia structure:
        - Content is in <div id="mw-content-text">
        - Paragraphs are <p> tags
        - Skip empty or reference-only paragraphs
        """
        # Find main content area
        content_div = soup.find("div", {"id": "mw-content-text"})
        if not content_div:
            content_div = soup.find("div", {"class": "mw-parser-output"})
        if not content_div:
            # Fallback: search whole document
            content_div = soup

        # Find all paragraphs
        paragraphs = content_div.find_all("p")

        for p in paragraphs:
            if not isinstance(p, Tag):
                continue

            # Get text content with proper spacing between elements
            text = p.get_text(separator=" ", strip=True)
            # Normalize multiple spaces to single space
            text = " ".join(text.split())

            # Skip empty paragraphs
            if not text:
                continue

            # Skip very short paragraphs (likely coordinates, dates, etc.)
            if len(text) < 50:
                continue

            # Skip paragraphs that are mostly references [1][2][3]
            import re
            clean_text = re.sub(r"\[\d+\]", "", text).strip()
            # If more than 30% of the paragraph is references, skip it
            if len(clean_text) < len(text) * 0.7:
                continue
            # Also skip if the clean text is too short after removing references
            if len(clean_text) < 50:
                continue

            return text

        raise ExtractionError("Could not find first paragraph")


class ExtractionError(Exception):
    """Error during content extraction."""

    pass

