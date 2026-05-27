"""SQLAlchemy models for Academic Hunter."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, String, Text, Float, Integer, JSON, Date, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    # User-level AI configuration (overrides server defaults when set)
    ai_api_key: Mapped[str | None] = mapped_column(String(255), default=None)
    ai_base_url: Mapped[str | None] = mapped_column(String(512), default=None)
    ai_model: Mapped[str | None] = mapped_column(String(100), default=None)

    # Semantic Scholar API key (optional, increases rate limits)
    s2_api_key: Mapped[str | None] = mapped_column(String(255), default=None)

    topic_subscriptions: Mapped[list[TopicSubscription]] = relationship(back_populates="user", cascade="all, delete-orphan")
    researcher_subscriptions: Mapped[list[ResearcherSubscription]] = relationship(back_populates="user", cascade="all, delete-orphan")


class TopicSubscription(Base):
    __tablename__ = "topic_subscriptions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    ai_keywords: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    journal_name: Mapped[str | None] = mapped_column(String(300), default=None)  # For journal sources
    semantic_embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="topic_subscriptions")


class ResearcherSubscription(Base):
    __tablename__ = "researcher_subscriptions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    researcher_name: Mapped[str] = mapped_column(String(200), nullable=False)
    orcid: Mapped[str | None] = mapped_column(String(20), default=None)
    s2_author_id: Mapped[str | None] = mapped_column(String(50), default=None)
    dblp_pid: Mapped[str | None] = mapped_column(String(50), default=None)
    ai_keywords: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates="researcher_subscriptions")


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    doi: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    abstract: Mapped[str | None] = mapped_column(Text, default=None)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    venue: Mapped[str | None] = mapped_column(String(300), default=None)
    venue_type: Mapped[str | None] = mapped_column(String(20), default=None)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ai_abstract_zh: Mapped[str | None] = mapped_column(Text, default=None)
    ai_tags: Mapped[list] = mapped_column(JSON, default=list)
    ai_evaluation: Mapped[str | None] = mapped_column(Text, default=None)
    credibility_score: Mapped[float | None] = mapped_column(Float, default=None)
    citation_count: Mapped[int | None] = mapped_column(Integer, default=None)
    source_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)


class DailyBrief(Base):
    __tablename__ = "daily_briefs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    subscription_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subscription_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    papers: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True)
    subscription_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subscription_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    week_start: Mapped[datetime] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
