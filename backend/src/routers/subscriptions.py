"""Subscription management and onboarding routers."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.models import User
from ..schemas import (
    OnboardingStartRequest,
    OnboardingStartResponse,
    ResearcherSubscriptionCreate,
    ResearcherSubscriptionResponse,
    ResearcherSubscriptionUpdate,
    TopicSubscriptionCreate,
    TopicSubscriptionResponse,
    TopicSubscriptionUpdate,
)
from ..services.ai import AIService
from ..services.auth_middleware import get_current_user
from ..services.subscriptions import (
    create_researcher_subscription,
    create_topic_subscription,
    delete_researcher_subscription,
    delete_topic_subscription,
    get_researcher_subscription,
    get_researcher_subscriptions,
    get_topic_subscription,
    get_topic_subscriptions,
    update_researcher_subscription,
    update_topic_subscription,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


def _get_user_ai(current_user: User = Depends(get_current_user)) -> AIService:
    """Dependency: create an AIService configured for the current user."""
    return AIService.from_user(current_user)


# ── Topic Subscriptions ──

@router.get("/topics", response_model=list[TopicSubscriptionResponse])
async def list_topic_subs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_topic_subscriptions(db, current_user.id)


@router.post("/topics", response_model=TopicSubscriptionResponse, status_code=201)
async def create_topic_sub(
    payload: TopicSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await create_topic_subscription(
        db,
        user_id=current_user.id,
        query_text=payload.query_text,
        ai_keywords=payload.ai_keywords,
        journal_name=payload.journal_name,
    )
    return sub


@router.get("/topics/{sub_id}", response_model=TopicSubscriptionResponse)
async def get_topic_sub(
    sub_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_topic_subscription(db, sub_id, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="Topic subscription not found")
    return sub


@router.patch("/topics/{sub_id}", response_model=TopicSubscriptionResponse)
async def update_topic_sub(
    sub_id: str,
    payload: TopicSubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_topic_subscription(db, sub_id, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="Topic subscription not found")
    return await update_topic_subscription(db, sub, **payload.model_dump(exclude_none=True))


@router.delete("/topics/{sub_id}", status_code=204)
async def delete_topic_sub(
    sub_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_topic_subscription(db, sub_id, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="Topic subscription not found")
    await delete_topic_subscription(db, sub)


# ── Researcher Subscriptions ──

@router.get("/researchers", response_model=list[ResearcherSubscriptionResponse])
async def list_researcher_subs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_researcher_subscriptions(db, current_user.id)


@router.post("/researchers", response_model=ResearcherSubscriptionResponse, status_code=201)
async def create_researcher_sub(
    payload: ResearcherSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await create_researcher_subscription(
        db,
        user_id=current_user.id,
        researcher_name=payload.researcher_name,
        orcid=payload.orcid,
        s2_author_id=payload.s2_author_id,
        dblp_pid=payload.dblp_pid,
        ai_keywords=payload.ai_keywords,
    )
    return sub


@router.get("/researchers/{sub_id}", response_model=ResearcherSubscriptionResponse)
async def get_researcher_sub(
    sub_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_researcher_subscription(db, sub_id, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="Researcher subscription not found")
    return sub


@router.patch("/researchers/{sub_id}", response_model=ResearcherSubscriptionResponse)
async def update_researcher_sub(
    sub_id: str,
    payload: ResearcherSubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_researcher_subscription(db, sub_id, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="Researcher subscription not found")
    return await update_researcher_subscription(db, sub, **payload.model_dump(exclude_none=True))


@router.delete("/researchers/{sub_id}", status_code=204)
async def delete_researcher_sub(
    sub_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_researcher_subscription(db, sub_id, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="Researcher subscription not found")
    await delete_researcher_subscription(db, sub)


# ── Onboarding ──

@router.post("/onboarding/expand", response_model=OnboardingStartResponse)
async def expand_topic(
    payload: OnboardingStartRequest,
    current_user: User = Depends(get_current_user),
    ai: AIService = Depends(_get_user_ai),
):
    """AI expands a natural language query into keywords, subfields, and suggested researchers."""
    try:
        result = await ai.expand_topic(payload.query_text)
    except Exception:
        # Fallback if AI is not configured
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
