"""Pipeline and brief routers."""

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session, get_db
from ..models.models import DailyBrief, User
from ..schemas import DailyBriefResponse
from ..services.ai import AIService
from ..services.auth_middleware import get_current_user
from ..services.pipeline import PipelineService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run", status_code=202)
async def trigger_daily_run(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Trigger the daily pipeline run for the current user (async background)."""
    user_id = current_user.id

    async def _run():
        try:
            async with async_session() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalar_one_or_none()
                if user is None:
                    logger.warning("Pipeline: user %s not found in background session", user_id)
                    return
                ai = AIService.from_user(user)
                svc = PipelineService(session, ai_service=ai)
                logger.info("Pipeline: starting run_daily_for_all for user %s", user_id)
                briefs = await svc.run_daily_for_all(user_id)
                logger.info("Pipeline: completed — %d briefs generated", len(briefs))
        except Exception as e:
            logger.exception("Pipeline background task failed: %s", e)

    background_tasks.add_task(_run)
    return {"message": "Daily pipeline started"}


@router.post("/debug-run")
async def debug_run(current_user: User = Depends(get_current_user)):
    """DEBUG: Run pipeline synchronously and return results."""
    from ..database import async_session as _session_factory

    async with _session_factory() as session:
        result = await session.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one_or_none()
        if user is None:
            return {"error": "user not found"}

        ai = AIService.from_user(user)
        svc = PipelineService(session, ai_service=ai)

        # Check subscriptions
        from ..models.models import TopicSubscription as TS
        subs_result = await session.execute(
            select(TS).where(TS.user_id == user.id, TS.status == "active")
        )
        subs = list(subs_result.scalars().all())

        info = {
            "subscriptions": len(subs),
            "subs_detail": [
                {"query": s.query_text, "keywords": s.ai_keywords}
                for s in subs
            ],
        }

        try:
            briefs = await svc.run_daily_for_all(user.id)
            info["briefs"] = len(briefs)
        except Exception as e:
            info["error"] = str(e)

        return info


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
