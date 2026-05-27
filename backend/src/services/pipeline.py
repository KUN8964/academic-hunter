"""Pipeline orchestrator: fetch, dedup, score, summarize, generate briefs."""

from datetime import datetime, timedelta, timezone
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.models import (
    DailyBrief,
    Paper,
    ResearcherSubscription,
    TopicSubscription,
)
from ..scrapers.arxiv import ArxivScraper
from ..scrapers.pubmed import PubMedScraper
from ..scrapers.semantic_scholar import SemanticScholarScraper
from ..utils import dedup_papers, utcnow
from .ai import AIService


# ── Protocol interfaces for dependency injection ──


class ScraperProtocol(Protocol):
    """Interface that any paper scraper must implement."""

    async def search(self, query: str, max_results: int, since: datetime | None = None) -> list[dict]: ...
    async def search_author(self, author_name: str, max_results: int, since: datetime | None = None) -> list[dict]: ...


class AIServiceProtocol(Protocol):
    """Interface for AI scoring and summarization."""

    async def score_paper(self, title: str, abstract: str, venue: str | None = None) -> dict: ...
    async def summarize_paper_zh(self, title: str, abstract: str) -> dict: ...
    async def evaluate_paper(self, title: str, abstract: str) -> str: ...
    async def generate_daily_brief(self, papers: list[dict], subscription_name: str, date: str) -> str: ...


class PipelineService:
    """Orchestrates the full paper discovery and briefing pipeline.

    Accepts dependencies via constructor for testability and extensibility.
    Falls back to production defaults when not injected.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        ai_service: AIServiceProtocol | None = None,
        arxiv_scraper: ScraperProtocol | None = None,
        s2_scraper: ScraperProtocol | None = None,
        s2_api_key: str = "",
        pubmed_scraper: ScraperProtocol | None = None,
    ) -> None:
        self.db = db
        self.ai = ai_service or AIService()
        self.arxiv = arxiv_scraper or ArxivScraper()
        self.s2 = s2_scraper or SemanticScholarScraper(api_key=s2_api_key)
        self.pubmed = pubmed_scraper or PubMedScraper()

    # ──────────────────────────────── Public API ────────────────────────────────

    async def run_daily_for_all(self, user_id: str) -> list[DailyBrief]:
        """Run daily brief generation for all of a user's active subscriptions.

        Checks S2 credit budget before running. Skips if credits are below threshold.
        """
        # Credit budget check
        if not await self._has_sufficient_credits():
            return []

        briefs: list[DailyBrief] = []

        for sub in await self._get_active_topic_subs(user_id):
            if not self._can_continue():
                break
            try:
                brief = await self.run_daily_brief_for_topic(sub)
                if brief:
                    briefs.append(brief)
            except Exception:
                continue

        for sub in await self._get_active_researcher_subs(user_id):
            if not self._can_continue():
                break
            try:
                brief = await self.run_daily_brief_for_researcher(sub)
                if brief:
                    briefs.append(brief)
            except Exception:
                continue

        return briefs

    async def run_daily_brief_for_topic(self, subscription: TopicSubscription) -> DailyBrief | None:
        """Run the daily pipeline for a topic subscription."""
        since = None if settings.daily_window_hours == 0 else utcnow() - timedelta(hours=settings.daily_window_hours)

        # 1. Fetch from all sources
        all_papers = await self._fetch_topic_papers(subscription, since)
        if not all_papers:
            return None

        return await self._score_papers_and_generate_brief(
            all_papers=all_papers,
            user_id=subscription.user_id,
            subscription_type="topic",
            subscription_id=subscription.id,
            subscription_name=subscription.query_text,
        )

    async def run_daily_brief_for_researcher(self, subscription: ResearcherSubscription) -> DailyBrief | None:
        """Run the daily pipeline for a researcher subscription."""
        since = None if settings.daily_window_hours == 0 else utcnow() - timedelta(hours=settings.daily_window_hours)

        # 1. Fetch from all sources
        all_papers = await self._fetch_researcher_papers(subscription, since)
        if not all_papers:
            return None

        return await self._score_papers_and_generate_brief(
            all_papers=all_papers,
            user_id=subscription.user_id,
            subscription_type="researcher",
            subscription_id=subscription.id,
            subscription_name=subscription.researcher_name,
        )

    # ──────────────────────────────── Private: credits ───────────────────────────

    async def _has_sufficient_credits(self) -> bool:
        """Check if we have enough S2 credits to run the pipeline.
        Returns False if credits are tracked and below budget.
        Returns True if credit tracking is unavailable (native S2 API).
        """
        if not hasattr(self.s2, "check_credits"):
            return True  # Non-S2 scraper — no credit tracking
        try:
            credits = await self.s2.check_credits()  # type: ignore[attr-defined]
        except Exception:
            return True  # Can't check — assume OK (native S2)
        if credits is None:
            return True  # No credit headers — native S2 API
        return credits >= settings.s2_credit_budget

    def _can_continue(self) -> bool:
        """Check mid-pipeline if we still have credits to continue."""
        if not hasattr(self.s2, "credits_remaining"):
            return True
        credits = self.s2.credits_remaining  # type: ignore[attr-defined]
        if credits is None:
            return True
        return credits >= settings.s2_credit_budget

    # ──────────────────────────────── Private: fetch ────────────────────────────

    async def _fetch_topic_papers(self, sub: TopicSubscription, since: datetime | None) -> list[dict]:
        """Fetch papers for a topic subscription.

        Merges all keywords into a single S2 query (OR-separated) to save credits.
        arXiv and PubMed use separate calls (free APIs), best-effort.
        """
        # Use ai_keywords if available, otherwise fall back to query_text
        keywords = sub.ai_keywords if sub.ai_keywords else [sub.query_text]
        keywords = [k for k in keywords if k.strip()]  # filter empty
        if not keywords and not sub.journal_name:
            return []  # nothing to search
        # If it's a journal source, use journal name as primary keyword
        if sub.journal_name and not keywords:
            keywords = [sub.journal_name]
        all_papers: list[dict] = []

        # S2: merge keywords into one query (costs 1 credit instead of N)
        if keywords:
            s2_keywords = keywords[:5]
            merged_query = " OR ".join(f'"{kw}"' if " " in kw else kw for kw in s2_keywords)
            try:
                all_papers.extend(await self.s2.search(merged_query, max_results=30, since=since))
            except Exception:
                pass

        # arXiv + PubMed: per-keyword (free APIs), best-effort
        for keyword in keywords[:3]:
            for scraper, name in [(self.arxiv, "arXiv"), (self.pubmed, "PubMed")]:
                try:
                    all_papers.extend(await scraper.search(keyword, max_results=10, since=since))
                except Exception:
                    pass

        return all_papers

    async def _fetch_researcher_papers(self, sub: ResearcherSubscription, since: datetime | None) -> list[dict]:
        """Fetch papers from all scrapers for a researcher subscription."""
        all_papers: list[dict] = []

        # arXiv + PubMed: best-effort
        for scraper, name in [(self.arxiv, "arXiv"), (self.pubmed, "PubMed")]:
            try:
                all_papers.extend(await scraper.search_author(sub.researcher_name, max_results=15, since=since))
            except Exception:
                pass

        # S2: primary source
        try:
            all_papers.extend(await self.s2.search_author(
                sub.researcher_name, author_id=sub.s2_author_id, max_results=15, since=since,
            ))
        except Exception:
            pass

        return all_papers

    # ──────────────────────────── Private: score & brief ────────────────────────

    async def _score_papers_and_generate_brief(
        self,
        all_papers: list[dict],
        user_id: str,
        subscription_type: str,
        subscription_id: str,
        subscription_name: str,
    ) -> DailyBrief | None:
        """Shared pipeline: dedup → score/save → filter → generate brief."""
        # 2. Deduplicate
        unique_papers = dedup_papers(all_papers)

        # 2.5 Journal filter: if topic has a journal_name, keep only papers from that journal
        if subscription_type == "topic":
            result = await self.db.execute(select(TopicSubscription).where(TopicSubscription.id == subscription_id))
            sub = result.scalar_one_or_none()
            if sub and sub.journal_name:
                journal_lower = sub.journal_name.lower()
                unique_papers = [
                    p for p in unique_papers
                    if (p.get("venue") and journal_lower in p["venue"].lower())
                    or (p.get("journal") and journal_lower in str(p["journal"]).lower())
                ]

        # 3. Score and save each paper
        scored_papers = []
        for p in unique_papers[: settings.brief_max_papers * 2]:
            try:
                existing = await self._find_existing_paper(p)
                if existing:
                    scored_papers.append(existing)
                    continue

                paper = await self._score_and_save_paper(p)
                if paper:
                    scored_papers.append(paper)
            except Exception:
                continue

        # 4. Sort by credibility and take top papers (no absolute threshold)
        scored_papers.sort(key=lambda x: x.credibility_score or 0, reverse=True)
        top_papers = scored_papers[: settings.brief_max_papers]

        # 5. Generate brief (skip AI if no key)
        if self.ai.api_key:
            papers_data = [
                {
                    "title": p.title,
                    "authors": [a.get("name", "") for a in (p.authors or [])],
                    "venue": p.venue or "Preprint",
                    "score": p.credibility_score or 0,
                    "summary_zh": p.ai_abstract_zh or "",
                }
                for p in top_papers
            ]
            try:
                brief_md = await self.ai.generate_daily_brief(
                    papers=papers_data,
                    subscription_name=subscription_name,
                    date=utcnow().strftime("%Y-%m-%d"),
                )
            except Exception:
                brief_md = f"## {subscription_name} 每日简报\n\n共 {len(top_papers)} 篇论文"
        else:
            brief_md = f"## {subscription_name} 每日简报\n\n共 {len(top_papers)} 篇论文"

        # 6. Save brief (skip if no papers)
        if not top_papers:
            return None

        brief = DailyBrief(
            user_id=user_id,
            subscription_type=subscription_type,
            subscription_id=subscription_id,
            date=utcnow().date(),
            papers=[
                {"paper_id": p.id, "rank": i + 1, "credibility_score": p.credibility_score}
                for i, p in enumerate(top_papers)
            ],
        )
        self.db.add(brief)
        await self.db.commit()
        await self.db.refresh(brief)

        return brief

    async def _score_and_save_paper(self, p: dict) -> Paper | None:
        """Score, summarize, evaluate, and persist a single paper.

        AI operations are best-effort — paper is saved even if AI is unavailable.
        """
        # AI scoring (best-effort) — skip entirely if no API key configured
        score = 0.0
        summary_zh = None
        tags: list = []
        evaluation = None
        if self.ai.api_key:
            try:
                score_result = await self.ai.score_paper(
                    title=p.get("title", ""), abstract=p.get("abstract", "") or "", venue=p.get("venue"),
                )
                score = score_result.get("score", 0)
            except Exception:
                pass
            try:
                summary_result = await self.ai.summarize_paper_zh(
                    p.get("title", ""), p.get("abstract", "") or "",
                )
                summary_zh = summary_result.get("summary_zh")
                tags = summary_result.get("tags", [])
            except Exception:
                pass
            try:
                evaluation = await self.ai.evaluate_paper(
                    p.get("title", ""), p.get("abstract", "") or "",
                )
            except Exception:
                pass

        credibility = self._calculate_credibility(
            venue=p.get("venue"), venue_type=p.get("venue_type"), citation_count=p.get("citation_count", 0),
        )

        paper = Paper(
            source_type=p.get("source_type", "unknown"),
            source_id=p.get("source_id", ""),
            doi=p.get("doi"),
            title=p.get("title", ""),
            authors=p.get("authors", []),
            abstract=p.get("abstract"),
            url=p.get("url", ""),
            venue=p.get("venue"),
            venue_type=p.get("venue_type"),
            published_at=datetime.fromisoformat(p["published_at"]) if p.get("published_at") else None,
            ai_abstract_zh=summary_zh,
            ai_tags=tags,
            ai_evaluation=evaluation,
            credibility_score=credibility,
            citation_count=p.get("citation_count"),
            source_metadata=p.get("metadata", {}),
        )
        self.db.add(paper)
        await self.db.commit()
        await self.db.refresh(paper)
        return paper

    # ──────────────────────────── Private: credibility ──────────────────────────

    @staticmethod
    def _calculate_credibility(
        venue: str | None,
        venue_type: str | None,
        citation_count: int | None,
    ) -> float:
        """Calculate credibility score using the mixed weighting model."""
        venue_score = 5.0  # Default neutral
        if venue_type == "conference":
            top_venues = [
                "neurips", "icml", "iclr", "cvpr", "iccv", "acl", "emnlp",
                "aaai", "ijcai", "sigmod", "sosp", "osdi",
            ]
            if venue and any(tv in venue.lower() for tv in top_venues):
                venue_score = 9.0
            elif venue:
                venue_score = 7.0
        elif venue_type == "journal":
            venue_score = 7.0
        elif venue_type == "preprint":
            venue_score = 3.0

        citation_score = min((citation_count or 0) / 10.0, 10.0)
        return round(0.5 * venue_score + 0.3 * citation_score + 2.0, 1)

    # ──────────────────────────────── Private: lookup ───────────────────────────

    async def _find_existing_paper(self, paper_data: dict) -> Paper | None:
        """Check if a paper already exists in the database."""
        doi = paper_data.get("doi")
        if doi:
            result = await self.db.execute(select(Paper).where(Paper.doi == doi))
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        source_type = paper_data.get("source_type")
        source_id = paper_data.get("source_id")
        if source_type and source_id:
            result = await self.db.execute(
                select(Paper).where(Paper.source_type == source_type, Paper.source_id == source_id)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        return None

    # ──────────────────────────────── Private: queries ──────────────────────────

    async def _get_active_topic_subs(self, user_id: str) -> list[TopicSubscription]:
        result = await self.db.execute(
            select(TopicSubscription).where(
                TopicSubscription.user_id == user_id,
                TopicSubscription.status == "active",
            )
        )
        return list(result.scalars().all())

    async def _get_active_researcher_subs(self, user_id: str) -> list[ResearcherSubscription]:
        result = await self.db.execute(
            select(ResearcherSubscription).where(
                ResearcherSubscription.user_id == user_id,
                ResearcherSubscription.status == "active",
            )
        )
        return list(result.scalars().all())
