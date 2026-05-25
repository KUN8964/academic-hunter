"""Pipeline orchestrator: fetch, dedup, score, summarize, generate briefs."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.models import (
    DailyBrief,
    Paper,
    ResearcherSubscription,
    ResearchReport,
    TopicSubscription,
)
from ..schemas import PaperResponse
from .ai import AIService
from ..scrapers.arxiv import ArxivScraper
from ..scrapers.semantic_scholar import SemanticScholarScraper


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PipelineService:
    """Orchestrates the full paper discovery and briefing pipeline."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.ai = AIService()
        self.arxiv = ArxivScraper()
        self.s2 = SemanticScholarScraper()

    async def run_daily_brief_for_topic(self, subscription: TopicSubscription) -> DailyBrief | None:
        """Run the daily pipeline for a topic subscription. Returns the generated brief or None."""
        since = utcnow() - timedelta(hours=settings.daily_window_hours)

        # 1. Fetch from all sources
        all_papers: list[dict] = []
        for keyword in subscription.ai_keywords[:3]:  # Use top 3 keywords
            arxiv_papers = await self.arxiv.search(keyword, max_results=15, since=since)
            all_papers.extend(arxiv_papers)
            s2_papers = await self.s2.search(keyword, max_results=15, since=since)
            all_papers.extend(s2_papers)

        if not all_papers:
            return None

        # 2. Deduplicate
        unique_papers = await self._dedup_papers(all_papers)

        # 3. Score and process each paper
        scored_papers = []
        for p in unique_papers[:settings.brief_max_papers * 2]:  # Over-fetch for filtering
            try:
                # Check if paper already exists
                existing = await self._find_existing_paper(p)
                if existing:
                    scored_papers.append(existing)
                    continue

                # AI scoring
                score_result = await self.ai.score_paper(
                    title=p.get("title", ""),
                    abstract=p.get("abstract", "") or "",
                    venue=p.get("venue"),
                )
                score = score_result.get("score", 0)

                # AI summarization
                summary_result = await self.ai.summarize_paper_zh(
                    title=p.get("title", ""),
                    abstract=p.get("abstract", "") or "",
                )

                # AI evaluation
                evaluation = await self.ai.evaluate_paper(
                    title=p.get("title", ""),
                    abstract=p.get("abstract", "") or "",
                )

                # Calculate credibility
                credibility = self._calculate_credibility(
                    venue=p.get("venue"),
                    venue_type=p.get("venue_type"),
                    citation_count=p.get("citation_count", 0),
                )

                # Save paper
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
                    ai_abstract_zh=summary_result.get("summary_zh"),
                    ai_tags=summary_result.get("tags", []),
                    ai_evaluation=evaluation,
                    credibility_score=credibility,
                    citation_count=p.get("citation_count"),
                    source_metadata=p.get("metadata", {}),
                )
                self.db.add(paper)
                await self.db.commit()
                await self.db.refresh(paper)
                scored_papers.append(paper)
            except Exception:
                continue

        # 4. Filter by threshold and sort by credibility
        threshold = settings.ai_score_threshold
        qualified = [p for p in scored_papers if p.credibility_score and p.credibility_score >= threshold]
        qualified.sort(key=lambda x: x.credibility_score or 0, reverse=True)

        # 5. Take top N
        top_papers = qualified[:settings.brief_max_papers]

        # 6. Generate brief markdown with AI
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
                subscription_name=subscription.query_text,
                date=utcnow().strftime("%Y-%m-%d"),
            )
        except Exception:
            brief_md = f"## {subscription.query_text} 每日简报\n\n共 {len(top_papers)} 篇论文"

        # 7. Save brief
        brief = DailyBrief(
            user_id=subscription.user_id,
            subscription_type="topic",
            subscription_id=subscription.id,
            date=utcnow().date(),
            papers=[{"paper_id": p.id, "rank": i + 1, "credibility_score": p.credibility_score} for i, p in enumerate(top_papers)],
        )
        self.db.add(brief)
        await db.commit()
        await db.refresh(brief)

        return brief

    async def run_daily_brief_for_researcher(self, subscription: ResearcherSubscription) -> DailyBrief | None:
        """Run the daily pipeline for a researcher subscription."""
        since = utcnow() - timedelta(hours=settings.daily_window_hours)

        # Fetch papers by this researcher
        all_papers: list[dict] = []
        arxiv_papers = await self.arxiv.search_author(subscription.researcher_name, max_results=15, since=since)
        all_papers.extend(arxiv_papers)
        s2_papers = await self.s2.search_author(
            subscription.researcher_name,
            author_id=subscription.s2_author_id,
            max_results=15,
            since=since,
        )
        all_papers.extend(s2_papers)

        if not all_papers:
            return None

        unique_papers = await self._dedup_papers(all_papers)

        scored_papers = []
        for p in unique_papers[:settings.brief_max_papers * 2]:
            try:
                existing = await self._find_existing_paper(p)
                if existing:
                    scored_papers.append(existing)
                    continue

                score_result = await self.ai.score_paper(p.get("title", ""), p.get("abstract", "") or "", p.get("venue"))
                summary_result = await self.ai.summarize_paper_zh(p.get("title", ""), p.get("abstract", "") or "")
                evaluation = await self.ai.evaluate_paper(p.get("title", ""), p.get("abstract", "") or "")
                credibility = self._calculate_credibility(p.get("venue"), p.get("venue_type"), p.get("citation_count", 0))

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
                    ai_abstract_zh=summary_result.get("summary_zh"),
                    ai_tags=summary_result.get("tags", []),
                    ai_evaluation=evaluation,
                    credibility_score=credibility,
                    citation_count=p.get("citation_count"),
                    source_metadata=p.get("metadata", {}),
                )
                self.db.add(paper)
                await self.db.commit()
                await self.db.refresh(paper)
                scored_papers.append(paper)
            except Exception:
                continue

        qualified = [p for p in scored_papers if p.credibility_score and p.credibility_score >= settings.ai_score_threshold]
        qualified.sort(key=lambda x: x.credibility_score or 0, reverse=True)
        top_papers = qualified[:settings.brief_max_papers]

        if not top_papers:
            return None

        papers_data = [
            {"title": p.title, "authors": [a.get("name", "") for a in (p.authors or [])], "venue": p.venue or "Preprint", "score": p.credibility_score or 0, "summary_zh": p.ai_abstract_zh or ""}
            for p in top_papers
        ]

        try:
            brief_md = await self.ai.generate_daily_brief(papers=papers_data, subscription_name=subscription.researcher_name, date=utcnow().strftime("%Y-%m-%d"))
        except Exception:
            brief_md = f"## {subscription.researcher_name} 每日简报\n\n共 {len(top_papers)} 篇论文"

        brief = DailyBrief(
            user_id=subscription.user_id,
            subscription_type="researcher",
            subscription_id=subscription.id,
            date=utcnow().date(),
            papers=[{"paper_id": p.id, "rank": i + 1, "credibility_score": p.credibility_score} for i, p in enumerate(top_papers)],
        )
        self.db.add(brief)
        await self.db.commit()
        await self.db.refresh(brief)
        return brief

    async def run_daily_for_all(self, user_id: str) -> list[DailyBrief]:
        """Run daily brief generation for all of a user's active subscriptions."""
        briefs: list[DailyBrief] = []

        # Topic subscriptions
        result = await self.db.execute(
            select(TopicSubscription).where(
                TopicSubscription.user_id == user_id,
                TopicSubscription.status == "active",
            )
        )
        for sub in result.scalars().all():
            try:
                brief = await self.run_daily_brief_for_topic(sub)
                if brief:
                    briefs.append(brief)
            except Exception:
                continue

        # Researcher subscriptions
        result = await self.db.execute(
            select(ResearcherSubscription).where(
                ResearcherSubscription.user_id == user_id,
                ResearcherSubscription.status == "active",
            )
        )
        for sub in result.scalars().all():
            try:
                brief = await self.run_daily_brief_for_researcher(sub)
                if brief:
                    briefs.append(brief)
            except Exception:
                continue

        return briefs

    def _calculate_credibility(
        self,
        venue: str | None,
        venue_type: str | None,
        citation_count: int,
    ) -> float:
        """Calculate credibility score using the mixed weighting model."""
        venue_score = 5.0  # Default neutral
        if venue_type == "conference":
            # Top CS conferences get higher scores
            top_venues = ["neurips", "icml", "iclr", "cvpr", "iccv", "acl", "emnlp", "aaai", "ijcai", "sigmod", "sosp", "osdi"]
            if venue and any(tv in venue.lower() for tv in top_venues):
                venue_score = 9.0
            elif venue:
                venue_score = 7.0
        elif venue_type == "journal":
            venue_score = 7.0  # Moderate default for journals
        elif venue_type == "preprint":
            venue_score = 3.0  # Lower for preprints

        citation_score = min(citation_count / 10.0, 10.0)  # Cap at 10

        # Weighted formula: 50% venue, 30% citations, 20% reserved for author (simplified for now)
        return round(0.5 * venue_score + 0.3 * citation_score + 2.0, 1)  # +2.0 is the author baseline

    async def _dedup_papers(self, papers: list[dict]) -> list[dict]:
        """Deduplicate papers: DOI exact match first, then title-based."""
        seen_dois: set[str] = set()
        seen_urls: set[str] = set()
        unique: list[dict] = []

        for p in papers:
            doi = p.get("doi")
            url = p.get("url", "")

            # DOI exact match
            if doi and doi in seen_dois:
                continue
            # URL match (same paper from different sources)
            if url and url in seen_urls:
                continue

            if doi:
                seen_dois.add(doi)
            if url:
                seen_urls.add(url)
            unique.append(p)

        return unique

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
