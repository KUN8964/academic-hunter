"""Public endpoints — no authentication required."""

import logging

from fastapi import APIRouter

from ..schemas import (
    OnboardingStartRequest,
    OnboardingStartResponse,
    PublicPaperItem,
    PublicSearchRequest,
    PublicSearchResponse,
)
from ..scrapers.arxiv import ArxivScraper
from ..scrapers.semantic_scholar import SemanticScholarScraper

logger = logging.getLogger(__name__)


def _dedup_papers(papers: list[dict]) -> list[dict]:
    seen_dois: set[str] = set()
    seen_urls: set[str] = set()
    unique: list[dict] = []
    for p in papers:
        doi = p.get("doi")
        url = p.get("url", "")
        if doi and doi in seen_dois:
            continue
        if url and url in seen_urls:
            continue
        if doi:
            seen_dois.add(doi)
        if url:
            seen_urls.add(url)
        unique.append(p)
    return unique


router = APIRouter(prefix="/public", tags=["public"])


@router.post("/search", response_model=PublicSearchResponse)
async def public_search(payload: PublicSearchRequest):
    """Search arXiv + Semantic Scholar with AI-expanded keywords. No account needed."""
    arxiv = ArxivScraper()
    s2 = SemanticScholarScraper()
    all_papers: list[dict] = []
    warnings: list[str] = []
    arxiv_ok = s2_ok = False

    for kw in payload.keywords[:5]:
        try:
            all_papers.extend(await arxiv.search(kw, max_results=8))
            arxiv_ok = True
        except Exception as e:
            logger.warning("arXiv search failed for '%s': %s", kw, e)
        try:
            all_papers.extend(await s2.search(kw, max_results=8))
            s2_ok = True
        except Exception as e:
            logger.warning("S2 search failed for '%s': %s", kw, e)

    if not arxiv_ok and not s2_ok:
        return PublicSearchResponse(
            papers=[], total=0,
            warning="数据源暂时不可用（arXiv 和 Semantic Scholar 均无法访问），请稍后重试"
        )
    if not arxiv_ok:
        warnings.append("arXiv 暂不可用，结果仅来自 Semantic Scholar")
    if not s2_ok:
        warnings.append("Semantic Scholar 暂不可用，结果仅来自 arXiv")

    unique = _dedup_papers(all_papers)

    papers = []
    for p in unique[:30]:
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
