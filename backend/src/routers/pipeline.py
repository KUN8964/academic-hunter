"""Pipeline and brief routers."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.models import DailyBrief, User
from ..schemas import DailyBriefResponse
from ..services.auth_middleware import get_current_user
from ..services.pipeline import PipelineService

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run", status_code=202)
async def trigger_daily_run(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the daily pipeline run for the current user."""
    pipeline = PipelineService(db)

    async def _run():
        async with db.bind.connect() as conn:
            async with AsyncSession(conn) as session:
                svc = PipelineService(session)
                await svc.run_daily_for_all(current_user.id)

    background_tasks.add_task(_run)
    return {"message": "Daily pipeline started"}


@router.get("/briefs", response_model=list[DailyBriefResponse])
async def list_briefs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all daily briefs for the current user."""
    result = await db.execute(
        select(DailyBrief)
        .where(DailyBrief.user_id == current_user.id)
        .order_by(DailyBrief.date.desc())
        .limit(50)
    )
    return list(result.scalars().all())


@router.get("/briefs/{brief_id}", response_model=DailyBriefResponse)
async def get_brief(
    brief_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific daily brief."""
    result = await db.execute(
        select(DailyBrief).where(
            DailyBrief.id == brief_id,
            DailyBrief.user_id == current_user.id,
        )
    )
    brief = result.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    return brief
