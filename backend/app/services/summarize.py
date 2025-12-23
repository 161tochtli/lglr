"""
Summarization service.

Encapsulates the business logic for text summarization:
1. Calls OpenAI client to generate summary
2. Persists the result to the repository
3. Logs domain events
"""
from dataclasses import dataclass

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.domain import events
from app.domain.models import Summary, create_summary
from app.infra.openai_client import OpenAIClient
from app.repos.ports import SummaryRepo

logger = structlog.get_logger(__name__)


@dataclass
class SummarizeService:
    """
    Service for text summarization.

    Uses dependency injection for testability:
    - openai_client: Can be stub or real
    - summary_repo: Can be in-memory or persistent
    """

    openai_client: OpenAIClient
    summary_repo: SummaryRepo

    def summarize(
        self,
        *,
        text: str,
        model: str | None = None,
        request_id: str | None = None,
    ) -> Summary:
        """
        Summarize text using OpenAI and persist the result.

        Args:
            text: The text to summarize.
            model: Optional model to use for summarization.
            request_id: Optional correlation ID for tracing.

        Returns:
            The created Summary object with generated summary.
        """
        # Determine effective model
        effective_model = model or self.openai_client.default_model

        # Generate summary via OpenAI client
        summary_text = self.openai_client.summarize(text, model=effective_model)

        # Create and persist summary entity
        summary = create_summary(
            text=text,
            summary=summary_text,
            model=effective_model,
            request_id=request_id,
        )
        self.summary_repo.add(summary)

        # Log domain event
        try:
            bind_contextvars(
                request_id=request_id or "-",
                summary_id=str(summary.id),
            )
            evt = events.assistant_summary_created(summary)
            logger.info(evt.name, **evt.payload)
        finally:
            clear_contextvars()

        return summary

