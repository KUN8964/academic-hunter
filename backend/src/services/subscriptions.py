"""Subscription CRUD operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.models import ResearcherSubscription, TopicSubscription


# ── Topic Subscriptions ──

async def get_topic_subscriptions(db: AsyncSession, user_id: str) -> list[TopicSubscription]:
    result = await db.execute(
        select(TopicSubscription).where(TopicSubscription.user_id == user_id).order_by(TopicSubscription.created_at.desc())
    )
    return list(result.scalars().all())


async def get_topic_subscription(db: AsyncSession, subscription_id: str, user_id: str) -> TopicSubscription | None:
    result = await db.execute(
        select(TopicSubscription).where(
            TopicSubscription.id == subscription_id,
            TopicSubscription.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_topic_subscription(
    db: AsyncSession, user_id: str, query_text: str, ai_keywords: list[str], embedding: list[float] | None = None,
    journal_name: str | None = None,
) -> TopicSubscription:
    sub = TopicSubscription(
        user_id=user_id,
        query_text=query_text,
        ai_keywords=ai_keywords,
        semantic_embedding=embedding,
        journal_name=journal_name,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


async def update_topic_subscription(
    db: AsyncSession, sub: TopicSubscription, **kwargs
) -> TopicSubscription:
    for key, value in kwargs.items():
        if value is not None and hasattr(sub, key):
            setattr(sub, key, value)
    await db.commit()
    await db.refresh(sub)
    return sub


async def delete_topic_subscription(db: AsyncSession, sub: TopicSubscription) -> None:
    await db.delete(sub)
    await db.commit()


# ── Researcher Subscriptions ──

async def get_researcher_subscriptions(db: AsyncSession, user_id: str) -> list[ResearcherSubscription]:
    result = await db.execute(
        select(ResearcherSubscription)
        .where(ResearcherSubscription.user_id == user_id)
        .order_by(ResearcherSubscription.created_at.desc())
    )
    return list(result.scalars().all())


async def get_researcher_subscription(db: AsyncSession, subscription_id: str, user_id: str) -> ResearcherSubscription | None:
    result = await db.execute(
        select(ResearcherSubscription).where(
            ResearcherSubscription.id == subscription_id,
            ResearcherSubscription.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_researcher_subscription(
    db: AsyncSession,
    user_id: str,
    researcher_name: str,
    orcid: str | None = None,
    s2_author_id: str | None = None,
    dblp_pid: str | None = None,
    ai_keywords: list[str] | None = None,
) -> ResearcherSubscription:
    sub = ResearcherSubscription(
        user_id=user_id,
        researcher_name=researcher_name,
        orcid=orcid,
        s2_author_id=s2_author_id,
        dblp_pid=dblp_pid,
        ai_keywords=ai_keywords or [],
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return sub


async def update_researcher_subscription(
    db: AsyncSession, sub: ResearcherSubscription, **kwargs
) -> ResearcherSubscription:
    for key, value in kwargs.items():
        if value is not None and hasattr(sub, key):
            setattr(sub, key, value)
    await db.commit()
    await db.refresh(sub)
    return sub


async def delete_researcher_subscription(db: AsyncSession, sub: ResearcherSubscription) -> None:
    await db.delete(sub)
    await db.commit()
