"""Semantic Scholar scraper for paper search, citation data, and author tracking."""

from datetime import datetime, timezone

import httpx

from ..config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SemanticScholarScraper:
    """Fetch papers and author data from Semantic Scholar API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def _headers(self) -> dict:
        h = {}
        if settings.s2_api_key:
            h["x-api-key"] = settings.s2_api_key
        return h

    async def search(
        self,
        query: str,
        max_results: int = 30,
        since: datetime | None = None,
    ) -> list[dict]:
        """Search Semantic Scholar for papers."""
        params = {
            "query": query,
            "limit": max_results,
            "fields": "title,authors,abstract,url,venue,journal,publicationDate,externalIds,citationCount,year",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/paper/search",
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        papers = []
        for item in data.get("data", []):
            pub_date = item.get("publicationDate")
            if pub_date and since:
                try:
                    dt = datetime.fromisoformat(pub_date)
                    if dt < since:
                        continue
                except ValueError:
                    pass

            authors = []
            for a in item.get("authors", []):
                authors.append({"name": a.get("name", ""), "s2_author_id": a.get("authorId")})

            external_ids = item.get("externalIds", {}) or {}
            doi = external_ids.get("DOI")
            arxiv_id = external_ids.get("ArXiv")

            venue = None
            venue_type = None
            if item.get("journal"):
                journal = item["journal"]
                venue = journal.get("name") or journal.get("journal")
                venue_type = "journal"
            elif item.get("venue"):
                venue = item["venue"]
                venue_type = "conference" if "conf" in (venue or "").lower() else "journal"

            papers.append({
                "source_type": "s2",
                "source_id": item.get("paperId", ""),
                "doi": doi,
                "title": item.get("title", ""),
                "authors": authors,
                "abstract": item.get("abstract"),
                "url": item.get("url", f"https://api.semanticscholar.org/{item.get('paperId', '')}"),
                "venue": venue,
                "venue_type": venue_type,
                "published_at": pub_date,
                "fetched_at": utcnow().isoformat(),
                "citation_count": item.get("citationCount"),
                "metadata": {
                    "external_ids": external_ids,
                    "year": item.get("year"),
                },
            })
        return papers

    async def search_author(
        self,
        author_name: str,
        author_id: str | None = None,
        max_results: int = 20,
        since: datetime | None = None,
    ) -> list[dict]:
        """Search for papers by a specific author on Semantic Scholar."""
        if author_id:
            return await self._get_author_papers(author_id, max_results, since)

        # Search for author first, then get their papers
        author_info = await self._find_author(author_name)
        if not author_info:
            return []
        return await self._get_author_papers(author_info["authorId"], max_results, since)

    async def _find_author(self, name: str) -> dict | None:
        """Find an author by name on Semantic Scholar."""
        params = {"query": name, "limit": 1}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/author/search",
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        authors = data.get("data", [])
        return authors[0] if authors else None

    async def _get_author_papers(
        self,
        author_id: str,
        max_results: int = 20,
        since: datetime | None = None,
    ) -> list[dict]:
        """Get papers by author ID."""
        params = {
            "authorId": author_id,
            "limit": max_results,
            "fields": "title,authors,abstract,url,venue,journal,publicationDate,externalIds,citationCount,year",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.BASE_URL}/author/{author_id}/papers",
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        papers = []
        for item in data.get("data", []):
            pub_date = item.get("publicationDate")
            if pub_date and since:
                try:
                    dt = datetime.fromisoformat(pub_date)
                    if dt < since:
                        continue
                except ValueError:
                    pass

            authors = []
            for a in item.get("authors", []):
                authors.append({"name": a.get("name", ""), "s2_author_id": a.get("authorId")})

            external_ids = item.get("externalIds", {}) or {}
            doi = external_ids.get("DOI")
            arxiv_id = external_ids.get("ArXiv")

            venue = None
            venue_type = None
            if item.get("journal"):
                venue = item["journal"].get("name") or item["journal"].get("journal")
                venue_type = "journal"

            papers.append({
                "source_type": "s2",
                "source_id": item.get("paperId", ""),
                "doi": doi,
                "title": item.get("title", ""),
                "authors": authors,
                "abstract": item.get("abstract"),
                "url": item.get("url", ""),
                "venue": venue,
                "venue_type": venue_type,
                "published_at": pub_date,
                "fetched_at": utcnow().isoformat(),
                "citation_count": item.get("citationCount"),
                "metadata": {"external_ids": external_ids, "year": item.get("year")},
            })
        return papers
