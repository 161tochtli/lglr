"""
Unit tests for application services.

Tests cover:
1. OpenAIClientStub
2. SummarizeService
"""
from __future__ import annotations

from app.domain.models import Summary
from app.infra.openai_client import OpenAIClientStub, create_openai_client
from app.repos.in_memory import InMemorySummaryRepo
from app.services.summarize import SummarizeService


# ---------------------------------------------------------------------------
# OpenAIClientStub
# ---------------------------------------------------------------------------


def test_openai_stub_returns_deterministic_summary() -> None:
    """OpenAIClientStub should return predictable summaries."""
    stub = OpenAIClientStub()

    summary = stub.summarize("Hola mundo, esto es una prueba.")

    assert "[Resumen de" in summary
    assert "palabras]" in summary
    assert "Hola mundo" in summary


def test_openai_stub_truncates_long_text() -> None:
    """OpenAIClientStub should truncate long input texts."""
    stub = OpenAIClientStub()
    long_text = "palabra " * 100  # 100 words

    summary = stub.summarize(long_text)

    assert "[Resumen de 100 palabras]" in summary
    assert "..." in summary  # Should be truncated


def test_openai_stub_uses_provided_model() -> None:
    """OpenAIClientStub should accept model parameter (for logging)."""
    stub = OpenAIClientStub()

    # Just verify it doesn't raise
    summary = stub.summarize("Test text", model="gpt-4")
    assert summary  # Should return something


def test_create_openai_client_returns_stub_for_stub_key() -> None:
    """Factory should return stub when api_key is 'stub'."""
    client = create_openai_client("stub")
    assert isinstance(client, OpenAIClientStub)


# ---------------------------------------------------------------------------
# SummarizeService
# ---------------------------------------------------------------------------


def test_summarize_service_calls_client_and_persists() -> None:
    """SummarizeService should call OpenAI client and persist result."""
    stub = OpenAIClientStub()
    repo = InMemorySummaryRepo()
    service = SummarizeService(openai_client=stub, summary_repo=repo)

    result = service.summarize(
        text="Texto de prueba para resumir.",
        model="test-model",
        request_id="req-123",
    )

    # Should return Summary
    assert isinstance(result, Summary)
    assert result.text == "Texto de prueba para resumir."
    assert "[Resumen de" in result.summary
    assert result.model == "test-model"
    assert result.request_id == "req-123"

    # Should be persisted
    saved = repo.get(result.id)
    assert saved is not None
    assert saved.id == result.id


def test_summarize_service_without_optional_params() -> None:
    """SummarizeService should work without model and request_id."""
    stub = OpenAIClientStub()
    repo = InMemorySummaryRepo()
    service = SummarizeService(openai_client=stub, summary_repo=repo)

    result = service.summarize(text="Solo texto.")

    # model defaults to stub-model when using OpenAIClientStub
    assert result.model == "stub-model"
    assert result.request_id is None
    assert result.summary  # Should have summary

