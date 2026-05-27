"""Public service — handles paper search without authentication.

Scrapers are injected for testability and to follow the same
dependency-injection pattern as PipelineService.
"""

import logging
from typing import Protocol

from ..scrapers.arxiv import ArxivScraper
from ..scrapers.pubmed import PubMedScraper
from ..scrapers.semantic_scholar import SemanticScholarScraper
from ..utils import dedup_papers

logger = logging.getLogger(__name__)


class ScraperProtocol(Protocol):
    """Interface that scrapers must implement (mirrors pipeline.py)."""

    async def search(self, query: str, max_results: int, since=None) -> list[dict]: ...
    async def search_author(self, author_name: str, max_results: int, since=None) -> list[dict]: ...


class PublicService:
    """Orchestrates public paper search across arXiv, Semantic Scholar, and PubMed."""

    def __init__(
        self,
        *,
        arxiv_scraper: ScraperProtocol | None = None,
        s2_scraper: ScraperProtocol | None = None,
        pubmed_scraper: ScraperProtocol | None = None,
    ) -> None:
        self.arxiv = arxiv_scraper or ArxivScraper()
        self.s2 = s2_scraper or SemanticScholarScraper()
        self.pubmed = pubmed_scraper or PubMedScraper()

    async def search(self, keywords: list[str], max_per_source: int = 8) -> tuple[list[dict], list[str]]:
        """Search all sources with the given keywords.

        Returns (papers, warnings). Papers are deduplicated.
        """
        all_papers: list[dict] = []
        arxiv_ok = s2_ok = pubmed_ok = False

        for kw in keywords[:5]:
            try:
                all_papers.extend(await self.arxiv.search(kw, max_results=max_per_source))
                arxiv_ok = True
            except Exception as e:
                logger.warning("arXiv search failed for '%s': %s", kw, e)
            try:
                all_papers.extend(await self.s2.search(kw, max_results=max_per_source))
                s2_ok = True
            except Exception as e:
                logger.warning("S2 search failed for '%s': %s", kw, e)
            try:
                all_papers.extend(await self.pubmed.search(kw, max_results=max_per_source))
                pubmed_ok = True
            except Exception as e:
                logger.warning("PubMed search failed for '%s': %s", kw, e)

        warnings: list[str] = []
        if not arxiv_ok and not s2_ok and not pubmed_ok:
            return [], ["数据源暂时不可用（arXiv、Semantic Scholar 和 PubMed 均无法访问），请稍后重试"]
        if not arxiv_ok:
            warnings.append("arXiv 暂不可用，结果仅来自 Semantic Scholar 和 PubMed")
        if not s2_ok:
            warnings.append("Semantic Scholar 暂不可用，结果仅来自 arXiv 和 PubMed")
        if not pubmed_ok:
            warnings.append("PubMed 暂不可用，结果仅来自 arXiv 和 Semantic Scholar")

        return dedup_papers(all_papers), warnings
