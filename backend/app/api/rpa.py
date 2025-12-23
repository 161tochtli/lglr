"""
API endpoint for triggering the RPA bot.
"""
import asyncio

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rpa.wikipedia_bot import WikipediaBot, WikipediaBotConfig, SummarizeResult

router = APIRouter(tags=["rpa"])
logger = structlog.get_logger(__name__)


class RPARequest(BaseModel):
    search_term: str = Field(min_length=1, max_length=200)


class RPAResponse(BaseModel):
    search_term: str
    wikipedia_title: str
    wikipedia_url: str
    original_paragraph: str
    summary: str
    summary_id: str


@router.post("/rpa/wikipedia-summarize", response_model=RPAResponse, status_code=200)
async def run_rpa_endpoint(body: RPARequest) -> RPAResponse:
    """
    Run the Wikipedia RPA bot to search, extract, and summarize.

    1. Searches Wikipedia for the given term
    2. Extracts the first paragraph
    3. Summarizes it using OpenAI
    """
    try:
        config = WikipediaBotConfig(
            api_base_url="http://localhost:8000",  # Internal API call
        )
        bot = WikipediaBot(config=config)
        result = await bot.search_and_summarize(body.search_term)

        return RPAResponse(
            search_term=result.search_term,
            wikipedia_title=result.wikipedia_title,
            wikipedia_url=result.wikipedia_url,
            original_paragraph=result.original_paragraph,
            summary=result.summary,
            summary_id=result.summary_id,
        )
    except Exception as e:
        error_msg = str(e)
        logger.error("rpa.failed", error=error_msg, search_term=body.search_term)
        
        # Check for OpenAI quota errors (passed through from summarize endpoint)
        if "429" in error_msg or "quota" in error_msg.lower():
            raise HTTPException(
                status_code=429,
                detail="OpenAI quota exceeded. Please check your billing or use stub mode.",
            )
        
        raise HTTPException(status_code=500, detail=f"RPA failed: {error_msg}")

