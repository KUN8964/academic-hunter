"""Paper search and detail router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.models import Paper, User
from ..schemas import PaperResponse, SearchResponse
from ..services.auth_middleware import get_current_user

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("", response_model=SearchResponse)
async def search_papers(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search papers by title or abstract (case-insensitive ILIKE)."""
    search_term = f"%{q}%"

    count_result = await db.execute(
        select(func.count(Paper.id)).where(
            (Paper.title.ilike(search_term)) | (Paper.abstract.ilike(search_term))
        )
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Paper)
        .where((Paper.title.ilike(search_term)) | (Paper.abstract.ilike(search_term)))
        .order_by(Paper.credibility_score.desc().nulls_last())
        .limit(limit)
    )
    papers = list(result.scalars().all())

    return SearchResponse(results=[PaperResponse.model_validate(p) for p in papers], total=total)


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper(
    paper_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single paper by ID."""
    result = await db.execute(select(Paper).where(Paper.id == paper_id))
    paper = result.scalar_one_or_none()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper
