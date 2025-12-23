from __future__ import annotations

import structlog
from asgi_correlation_id import correlation_id
from fastapi import APIRouter, HTTPException, Request

from app.domain.models import NewSummary, Summary
from app.infra.openai_client import OpenAIError
from app.services.summarize import SummarizeService

router = APIRouter(tags=["assistant"])
logger = structlog.get_logger(__name__)


def _get_service(request: Request) -> SummarizeService:
    """Get SummarizeService from app state."""
    return request.app.state.summarize_service


@router.post("/assistant/summarize", response_model=Summary, status_code=201)
def create_summary_endpoint(request: Request, body: NewSummary) -> Summary:
    """
    Summarize text using OpenAI (or stub in tests).

    The service handles:
    - Calling OpenAI client
    - Persisting the summary
    - Logging domain events
    """
    service = _get_service(request)
    rid = correlation_id.get() or None

    try:
        return service.summarize(
            text=body.text,
            model=body.model,
            request_id=rid,
        )
    except OpenAIError as e:
        error_msg = str(e)
        if "429" in error_msg:
            raise HTTPException(
                status_code=429,
                detail="OpenAI quota exceeded. Please check your billing or use stub mode.",
            )
        raise HTTPException(status_code=502, detail=f"OpenAI API error: {error_msg}")
