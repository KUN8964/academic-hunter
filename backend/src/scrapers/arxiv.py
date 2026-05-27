"""Academic data source scrapers: arXiv, Semantic Scholar."""

from datetime import datetime, timezone

import httpx

from ..config import settings
from ..utils import utcnow


class ArxivScraper:
    """Fetch papers from arXiv API."""

    BASE_URL = "https://export.arxiv.org/api/query"

    async def search(self, query: str, max_results: int = 30, since: datetime | None = None) -> list[dict]:
        """Search arXiv for papers matching the query."""
        import feedparser

        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        papers = []
        for entry in feed.entries:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc) if hasattr(entry, "published_parsed") else None
            if since and published and published < since:
                continue

            # Extract arXiv ID from the ID URL
            arxiv_id = entry.id.split("/abs/")[-1] if "/abs/" in entry.id else entry.id

            authors = [{"name": a.name} for a in entry.authors] if hasattr(entry, "authors") else []

            papers.append({
                "source_type": "arxiv",
                "source_id": arxiv_id,
                "title": entry.title.strip().replace("\n", " "),
                "authors": authors,
                "abstract": entry.summary.strip() if hasattr(entry, "summary") else None,
                "url": entry.id,
                "venue": None,
                "venue_type": "preprint",
                "published_at": published.isoformat() if published else None,
                "fetched_at": utcnow().isoformat(),
                "metadata": {
                    "categories": [t.term for t in entry.tags] if hasattr(entry, "tags") else [],
                    "primary_category": entry.arxiv_primary_category.get("term") if hasattr(entry, "arxiv_primary_category") else None,
                },
            })
        return papers

    async def search_author(self, author_name: str, max_results: int = 20, since: datetime | None = None) -> list[dict]:
        """Search arXiv for papers by a specific author."""
        import feedparser

        query = f'au:"{author_name}"'
        params = {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(self.BASE_URL, params=params)
            resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        papers = []
        for entry in feed.entries:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc) if hasattr(entry, "published_parsed") else None
            if since and published and published < since:
                continue

            arxiv_id = entry.id.split("/abs/")[-1] if "/abs/" in entry.id else entry.id
            authors = [{"name": a.name} for a in entry.authors] if hasattr(entry, "authors") else []

            papers.append({
                "source_type": "arxiv",
                "source_id": arxiv_id,
                "title": entry.title.strip().replace("\n", " "),
                "authors": authors,
                "abstract": entry.summary.strip() if hasattr(entry, "summary") else None,
                "url": entry.id,
                "venue": None,
                "venue_type": "preprint",
                "published_at": published.isoformat() if published else None,
                "fetched_at": utcnow().isoformat(),
                "metadata": {"categories": [t.term for t in entry.tags] if hasattr(entry, "tags") else []},
            })
        return papers
