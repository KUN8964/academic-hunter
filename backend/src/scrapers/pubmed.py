"""PubMed / NCBI scraper — E-utilities esearch + efetch pipeline."""

from datetime import datetime, timezone
import xml.etree.ElementTree as ET

import httpx

from ..config import settings
from ..utils import utcnow


class PubMedScraper:
    """Fetch papers from PubMed via NCBI E-utilities API.

    Two-step pipeline:
      1. esearch — find PMIDs matching query
      2. efetch — get full article details by PMID

    Rate limits: 3 req/sec without API key, 10 req/sec with.
    """

    ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    EFETCH_URL  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def _api_params(self) -> dict[str, str]:
        """Return common API-key / email params when configured."""
        params: dict[str, str] = {}
        if settings.ncbi_email:
            params["email"]  = settings.ncbi_email
        if settings.ncbi_api_key:
            params["api_key"] = settings.ncbi_api_key
        return params

    # ──────────────────────────────── Public API ────────────────────────────────

    async def search(
        self,
        query: str,
        max_results: int = 30,
        since: datetime | None = None,
    ) -> list[dict]:
        """Search PubMed by keyword query.

        Args:
            query: free-text search term (supports PubMed query syntax).
            max_results: max PMIDs to fetch.
            since: only return papers published on or after this date.
        """
        # ── Step 1: esearch ──
        params = {
            "db":        "pubmed",
            "term":      query,
            "retmax":    str(min(max_results, 100)),
            "sort":      "pub+date",
            "retmode":   "xml",
            **self._api_params(),
        }
        if since:
            mindate = since.strftime("%Y/%m/%d")
            maxdate = utcnow().strftime("%Y/%m/%d")
            params["mindate"] = mindate
            params["maxdate"] = maxdate
            params["datetype"] = "pdat"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.ESEARCH_URL, params=params)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        pmids = [e.text for e in root.findall(".//Id") if e.text]
        if not pmids:
            return []

        # ── Step 2: efetch ──
        return await self._fetch_by_pmids(pmids)

    async def search_author(
        self,
        author_name: str,
        max_results: int = 20,
        since: datetime | None = None,
    ) -> list[dict]:
        """Search PubMed for papers by a specific author.

        Uses PubMed's author field qualifier: "lastname firstInitial"[Author].
        """
        # Best-effort: treat the whole string as author search
        query = f'"{author_name}"[Author]'
        return await self.search(query, max_results=max_results, since=since)

    # ──────────────────────────────── Internal ─────────────────────────────────

    async def _fetch_by_pmids(self, pmids: list[str]) -> list[dict]:
        """Fetch full article XML for a list of PMIDs."""
        params = {
            "db":      "pubmed",
            "id":      ",".join(pmids),
            "rettype": "abstract",
            "retmode": "xml",
            **self._api_params(),
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.EFETCH_URL, params=params)
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        papers: list[dict] = []
        for article in root.findall(".//PubmedArticle"):
            paper = self._parse_article(article)
            if paper:
                papers.append(paper)
        return papers

    # ──────────────────────────────── XML parsing ──────────────────────────────

    def _parse_article(self, article: ET.Element) -> dict | None:
        """Parse a <PubmedArticle> element into the standard paper dict."""
        medline = article.find(".//MedlineCitation")
        art      = article.find(".//Article")
        if medline is None or art is None:
            return None

        pmid = (medline.findtext("PMID") or "").strip()

        # ── Title ──
        title_el = art.find(".//ArticleTitle")
        title = "".join(title_el.itertext()).strip() if title_el is not None else ""

        # ── Abstract ──
        abstract: str | None = None
        abs_el = art.find(".//Abstract")
        if abs_el is not None:
            parts = []
            for at in abs_el.findall("AbstractText"):
                label = at.get("Label", "")
                text  = "".join(at.itertext()).strip()
                parts.append(f"{label}: {text}" if label else text)
            abstract = "\n".join(parts) if parts else None

        # ── Authors ──
        authors: list[dict] = []
        for au in art.findall(".//Author"):
            last  = (au.findtext("LastName")  or "").strip()
            fore  = (au.findtext("ForeName")  or "").strip()
            name  = f"{last} {fore}".strip() or (au.findtext("CollectiveName") or "").strip()
            if name:
                authors.append({"name": name})

        # ── Journal / Venue ──
        journal_el = art.find(".//Journal")
        journal_name: str | None = None
        if journal_el is not None:
            journal_name = (
                journal_el.findtext("Title")
                or journal_el.findtext("ISOAbbreviation")
            )
            if journal_name:
                journal_name = journal_name.strip()

        # ── DOI ──
        doi: str | None = None
        for eid in article.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi" and eid.text:
                doi = eid.text.strip()
        if not doi:
            for aid in article.findall(".//ArticleId"):
                if aid.get("IdType") == "doi" and aid.text:
                    doi = aid.text.strip()

        # ── Publication date ──
        pub_date_el = art.find(".//Journal/JournalIssue/PubDate")
        published_at = self._parse_pub_date(pub_date_el)

        # ── MeSH terms / keywords ──
        mesh_terms: list[str] = []
        for mh in medline.findall(".//MeshHeading/DescriptorName"):
            t = (mh.text or "").strip()
            if t:
                mesh_terms.append(t)

        return {
            "source_type":    "pubmed",
            "source_id":      pmid,
            "doi":            doi,
            "title":          title,
            "authors":        authors,
            "abstract":       abstract,
            "url":            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "venue":          journal_name,
            "venue_type":     "journal",
            "published_at":   published_at.isoformat() if published_at else None,
            "fetched_at":     utcnow().isoformat(),
            "citation_count": None,   # PubMed API doesn't expose citation count
            "metadata": {
                "pmid":       pmid,
                "mesh_terms": mesh_terms,
            },
        }

    @staticmethod
    def _parse_pub_date(el: ET.Element | None) -> datetime | None:
        """Parse <PubDate> with various child element combinations."""
        if el is None:
            return None
        year  = (el.findtext("Year")  or "").strip()
        month = (el.findtext("Month") or "").strip() or "1"
        day   = (el.findtext("Day")   or "").strip() or "1"
        if not year:
            medline_date = (el.findtext("MedlineDate") or "").strip()
            if medline_date:
                year = medline_date[:4]
        if not year:
            return None
        try:
            return datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
        except (ValueError, OverflowError):
            return None
