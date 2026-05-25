"""Public endpoints — no authentication required."""

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
from ..services.ai import AIService

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/onboarding/expand", response_model=OnboardingStartResponse)
async def public_expand(payload: OnboardingStartRequest):
    """Expand a research topic using the API key provided in the request."""
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


@router.post("/search", response_model=PublicSearchResponse)
async def public_search(payload: PublicSearchRequest):
    """Search arXiv + Semantic Scholar with AI-expanded keywords. No account needed."""
    arxiv = ArxivScraper()
    s2 = SemanticScholarScraper()

    all_papers: list[dict] = []
    for kw in payload.keywords[:5]:
        try:
            all_papers.extend(await arxiv.search(kw, max_results=8))
        except Exception:
            pass
        try:
            all_papers.extend(await s2.search(kw, max_results=8))
        except Exception:
            pass

    # Dedup by DOI and URL
    seen_dois: set[str] = set()
    seen_urls: set[str] = set()
    unique: list[dict] = []
    for p in all_papers:
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

    return PublicSearchResponse(papers=papers, total=len(papers))
