"""
OpenAI client abstraction for text summarization.

Provides:
- OpenAIClient: Protocol for summarization
- OpenAIClientStub: Deterministic stub for tests
- OpenAIClientReal: Real OpenAI API integration
"""
from dataclasses import dataclass
from typing import Protocol

import httpx
import structlog

logger = structlog.get_logger(__name__)


class OpenAIClient(Protocol):
    """Protocol for OpenAI-like summarization clients."""

    default_model: str

    def summarize(self, text: str, *, model: str | None = None) -> str:
        """
        Generate a summary of the given text.

        Args:
            text: The text to summarize.
            model: Optional model identifier.

        Returns:
            The generated summary.
        """
        ...


@dataclass
class OpenAIClientStub:
    """
    Deterministic stub for testing.

    Returns predictable summaries without network calls.
    Use this in tests for speed, reliability, and no API costs.
    """

    default_model: str = "stub-model"

    def summarize(self, text: str, *, model: str | None = None) -> str:
        """Return a deterministic summary based on input text."""
        # Normalize whitespace
        normalized = " ".join(text.strip().split())

        # Simple deterministic summarization: first 100 chars + word count
        word_count = len(normalized.split())

        if len(normalized) <= 100:
            summary = normalized
        else:
            summary = normalized[:100].rsplit(" ", 1)[0] + "..."

        effective_model = model or self.default_model
        logger.info(
            "openai.summarize.stub",
            input_length=len(text),
            word_count=word_count,
            model=effective_model,
        )

        return f"[Resumen de {word_count} palabras] {summary}"


@dataclass
class OpenAIClientReal:
    """
    Real OpenAI API client using httpx.

    Calls the OpenAI Chat Completions API for summarization.
    """

    api_key: str
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-3.5-turbo"
    timeout: float = 30.0

    def summarize(self, text: str, *, model: str | None = None) -> str:
        """Call OpenAI API to generate a summary."""
        effective_model = model or self.default_model

        # Truncate very long texts to stay within token limits
        max_input_chars = 12000  # ~3000 tokens
        if len(text) > max_input_chars:
            text = text[:max_input_chars] + "..."
            logger.warning(
                "openai.text_truncated",
                original_length=len(text),
                truncated_to=max_input_chars,
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "Eres un asistente que resume textos de forma concisa y precisa. "
                    "Responde solo con el resumen, sin explicaciones adicionales."
                ),
            },
            {
                "role": "user",
                "content": f"Resume el siguiente texto:\n\n{text}",
            },
        ]

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": effective_model,
                        "messages": messages,
                        "temperature": 0.3,  # Lower = more deterministic
                        "max_tokens": 500,
                    },
                )
                response.raise_for_status()
                data = response.json()

                summary = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})

                logger.info(
                    "openai.summarize.success",
                    model=effective_model,
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                )

                return summary

        except httpx.HTTPStatusError as e:
            logger.error(
                "openai.summarize.http_error",
                status_code=e.response.status_code,
                response_text=e.response.text[:200],
            )
            raise OpenAIError(f"OpenAI API error: {e.response.status_code}") from e

        except httpx.RequestError as e:
            logger.error("openai.summarize.request_error", error=str(e))
            raise OpenAIError(f"OpenAI request failed: {e}") from e


class OpenAIError(Exception):
    """Exception raised when OpenAI API call fails."""

    pass


def create_openai_client(api_key: str) -> OpenAIClient:
    """
    Factory function to create the appropriate OpenAI client.

    - If api_key is "stub" → returns OpenAIClientStub
    - Otherwise → returns OpenAIClientReal

    Args:
        api_key: OpenAI API key, or "stub" for testing.

    Returns:
        OpenAIClient implementation.
    """
    if api_key == "stub":
        logger.info("openai.client.using_stub")
        return OpenAIClientStub()

    logger.info("openai.client.using_real")
    return OpenAIClientReal(api_key=api_key)

