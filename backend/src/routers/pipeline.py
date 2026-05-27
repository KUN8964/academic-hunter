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
                svc = PipelineService(session, ai_service=ai, s2_api_key=user.s2_api_key or "")
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
        svc = PipelineService(session, ai_service=ai, s2_api_key=user.s2_api_key or "")

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
            import traceback
            info["traceback"] = traceback.format_exc()

        # Credit info
        if hasattr(svc.s2, "credits_remaining"):
            info["credits_remaining"] = svc.s2.credits_remaining
            info["credits_sufficient"] = await svc._has_sufficient_credits()

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


@router.delete("/briefs/{brief_id}", status_code=204)
async def delete_brief(
    brief_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific daily brief. Only the owner can delete."""
    result = await db.execute(
        select(DailyBrief).where(
            DailyBrief.id == brief_id,
            DailyBrief.user_id == current_user.id,
        )
    )
    brief = result.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    await db.delete(brief)
    await db.commit()


@router.post("/run/topic/{sub_id}")
async def run_single_topic(
    sub_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run pipeline for a single topic subscription. Returns the generated brief."""
    from ..models.models import TopicSubscription

    result = await db.execute(
        select(TopicSubscription).where(
            TopicSubscription.id == sub_id,
            TopicSubscription.user_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Topic subscription not found")

    ai = AIService.from_user(current_user)
    svc = PipelineService(db, ai_service=ai, s2_api_key=current_user.s2_api_key or "")

    credits_before = svc.s2.credits_remaining if hasattr(svc.s2, "credits_remaining") else None
    brief = await svc.run_daily_brief_for_topic(sub)
    credits_after = svc.s2.credits_remaining if hasattr(svc.s2, "credits_remaining") else None

    if brief is None:
        return {
            "brief": None,
            "message": "未找到新论文（24 小时内无新发表）",
            "credits_remaining": credits_after,
        }

    return {
        "brief": {
            "id": brief.id,
            "subscription_type": brief.subscription_type,
            "date": str(brief.date),
            "papers": brief.papers,
        },
        "credits_remaining": credits_after,
    }


@router.post("/run/researcher/{sub_id}")
async def run_single_researcher(
    sub_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run pipeline for a single researcher subscription. Returns the generated brief."""
    from ..models.models import ResearcherSubscription

    result = await db.execute(
        select(ResearcherSubscription).where(
            ResearcherSubscription.id == sub_id,
            ResearcherSubscription.user_id == current_user.id,
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Researcher subscription not found")

    ai = AIService.from_user(current_user)
    svc = PipelineService(db, ai_service=ai, s2_api_key=current_user.s2_api_key or "")

    credits_before = svc.s2.credits_remaining if hasattr(svc.s2, "credits_remaining") else None
    brief = await svc.run_daily_brief_for_researcher(sub)
    credits_after = svc.s2.credits_remaining if hasattr(svc.s2, "credits_remaining") else None

    if brief is None:
        return {
            "brief": None,
            "message": "未找到新论文（24 小时内无新发表）",
            "credits_remaining": credits_after,
        }

    return {
        "brief": {
            "id": brief.id,
            "subscription_type": brief.subscription_type,
            "date": str(brief.date),
            "papers": brief.papers,
        },
        "credits_remaining": credits_after,
    }
