"""
Unit tests for RPA WikipediaExtractor.

Tests cover:
1. Title extraction
2. First paragraph extraction
3. Error handling
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.rpa.extractor import ExtractionError, WikipediaExtractor


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_html() -> str:
    """Load sample Wikipedia HTML fixture."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / "wikipedia_sample.html"
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def extractor() -> WikipediaExtractor:
    """WikipediaExtractor instance."""
    return WikipediaExtractor()


# ---------------------------------------------------------------------------
# Title extraction
# ---------------------------------------------------------------------------


def test_extractor_extracts_title(extractor: WikipediaExtractor, sample_html: str) -> None:
    """Extractor should extract page title from HTML."""
    result = extractor.extract(sample_html)
    assert result.title == "Albert Einstein"


def test_extractor_raises_on_missing_title() -> None:
    """Extractor should raise ExtractionError if title not found."""
    extractor = WikipediaExtractor()
    html = "<html><body><p>No title here</p></body></html>"

    with pytest.raises(ExtractionError, match="Could not find page title"):
        extractor.extract(html)


def test_extractor_handles_title_fallback() -> None:
    """Extractor should fallback to <title> tag if no h1."""
    extractor = WikipediaExtractor()
    html = """
    <html>
    <head><title>Nikola Tesla - Wikipedia, la enciclopedia libre</title></head>
    <body>
        <div id="mw-content-text">
            <p>Nikola Tesla fue un inventor, ingeniero eléctrico y mecánico e ingeniero electromecánico serbio-estadounidense. Es conocido por sus contribuciones revolucionarias al desarrollo de los sistemas de corriente alterna.</p>
        </div>
    </body>
    </html>
    """

    result = extractor.extract(html)
    assert result.title == "Nikola Tesla"
    assert "inventor" in result.first_paragraph


# ---------------------------------------------------------------------------
# Paragraph extraction
# ---------------------------------------------------------------------------


def test_extractor_extracts_first_paragraph(extractor: WikipediaExtractor, sample_html: str) -> None:
    """Extractor should extract first meaningful paragraph."""
    result = extractor.extract(sample_html)

    # Should contain key content from the first real paragraph
    assert "Albert Einstein" in result.first_paragraph
    assert "físico teórico alemán" in result.first_paragraph
    assert "1879" in result.first_paragraph


def test_extractor_skips_short_paragraphs(extractor: WikipediaExtractor, sample_html: str) -> None:
    """Extractor should skip very short paragraphs."""
    result = extractor.extract(sample_html)

    # Should NOT be the short description paragraph
    assert result.first_paragraph != "Físico teórico alemán"


def test_extractor_raises_on_missing_paragraph() -> None:
    """Extractor should raise ExtractionError if no paragraph found."""
    extractor = WikipediaExtractor()
    html = """
    <html>
    <head><title>Test Page - Wikipedia</title></head>
    <body>
        <h1 id="firstHeading">Test</h1>
        <div id="mw-content-text">
            <p>Short.</p>
        </div>
    </body>
    </html>
    """

    with pytest.raises(ExtractionError, match="Could not find first paragraph"):
        extractor.extract(html)


# ---------------------------------------------------------------------------
# URL handling
# ---------------------------------------------------------------------------


def test_extractor_includes_url_in_result(extractor: WikipediaExtractor, sample_html: str) -> None:
    """Extractor should include URL in result if provided."""
    result = extractor.extract(sample_html, url="https://es.wikipedia.org/wiki/Albert_Einstein")
    assert result.url == "https://es.wikipedia.org/wiki/Albert_Einstein"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_extractor_handles_nested_content() -> None:
    """Extractor should handle deeply nested paragraph content."""
    extractor = WikipediaExtractor()
    html = """
    <html>
    <head><title>Test - Wikipedia</title></head>
    <body>
        <h1 id="firstHeading">Test Article</h1>
        <div id="mw-content-text">
            <div class="mw-parser-output">
                <div class="infobox">
                    <p>Infobox content to skip</p>
                </div>
                <p>This is a substantial first paragraph with enough content to be meaningful. It contains important information about the subject matter and spans multiple sentences to ensure it passes the length check.</p>
            </div>
        </div>
    </body>
    </html>
    """

    result = extractor.extract(html)
    assert "substantial first paragraph" in result.first_paragraph


def test_extractor_filters_reference_heavy_paragraphs() -> None:
    """Extractor should skip paragraphs that are mostly references."""
    extractor = WikipediaExtractor()
    html = """
    <html>
    <head><title>Test - Wikipedia</title></head>
    <body>
        <h1 id="firstHeading">Test</h1>
        <div id="mw-content-text">
            <p>[1][2][3][4][5][6][7][8][9][10] Mostly references paragraph with very little actual text content visible.</p>
            <p>This is a normal paragraph without excessive references. It contains meaningful content about the subject and is long enough to be considered substantial content for extraction purposes.</p>
        </div>
    </body>
    </html>
    """

    result = extractor.extract(html)
    assert "normal paragraph" in result.first_paragraph

