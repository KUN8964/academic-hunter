"""Public endpoints — no authentication required."""

import logging

from fastapi import APIRouter, Depends

from ..schemas import (
    OnboardingStartRequest,
    OnboardingStartResponse,
    PublicPaperItem,
    PublicSearchRequest,
    PublicSearchResponse,
)
from ..services.public import PublicService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["public"])


def _get_public_service() -> PublicService:
    """Dependency: create a PublicService with production scrapers."""
    return PublicService()


@router.post("/search", response_model=PublicSearchResponse)
async def public_search(
    payload: PublicSearchRequest,
    svc: PublicService = Depends(_get_public_service),
):
    """Search arXiv + Semantic Scholar with AI-expanded keywords. No account needed."""
    all_papers, warnings = await svc.search(payload.keywords)

    papers = []
    for p in all_papers[:30]:
        authors = [a.get("name", "") for a in p.get("authors", [])]
        papers.append(PublicPaperItem(
            title=p.get("title", ""),
            authors=authors[:5],
            abstract=p.get("abstract"),
            url=p.get("url", ""),
            venue=p.get("venue"),
            source_type=p.get("source_type", "unknown"),
            published_at=p.get("published_at"),
        ))

    return PublicSearchResponse(
        papers=papers,
        total=len(papers),
        warning="; ".join(warnings) if warnings else "",
    )


@router.post("/onboarding/expand", response_model=OnboardingStartResponse)
async def public_expand(payload: OnboardingStartRequest):
    """Expand a research topic using the API key provided in the request."""
    from ..services.ai import AIService

    ai = AIService(
        api_key=payload.ai_api_key or "",
        base_url=payload.ai_base_url or "",
        model=payload.ai_model or "",
    )
    try:
        result = await ai.expand_topic(payload.query_text)
    except Exception:
        return OnboardingStartResponse(
            ai_keywords=[payload.query_text],
            suggested_subfields=[],
            suggested_researchers=[],
        )
    return OnboardingStartResponse(
        ai_keywords=result.get("keywords", []),
        suggested_subfields=result.get("subfields", []),
        suggested_researchers=result.get("researchers", []),
    )
