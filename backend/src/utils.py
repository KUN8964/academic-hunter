"""Shared utilities — keep DRY."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return current UTC datetime. Single source of truth across the project."""
    return datetime.now(timezone.utc)


def dedup_papers(papers: list[dict]) -> list[dict]:
    """Deduplicate papers by DOI (exact match) then URL.

    Papers sharing a DOI or URL with an earlier paper are dropped.
    """
    seen_dois: set[str] = set()
    seen_urls: set[str] = set()
    unique: list[dict] = []

    for p in papers:
        doi = p.get("doi")
        url = p.get("url", "")

        if doi and doi in seen_dois:
            continue
        if url and url in seen_urls:
            continue

        if doi:
            seen_dois.add(doi)
        if url:
            seen_urls.add(url)
        unique.append(p)

    return unique
