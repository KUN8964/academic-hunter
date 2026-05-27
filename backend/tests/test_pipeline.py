"""Tests for pipeline logic: dedup, credibility scoring, paper finding."""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-unit-tests-only-minimum-32-chars!!")


class TestDedupPapers:
    """Paper deduplication logic (synchronous pure functions)."""

    def test_doi_exact_match(self):
        from src.utils import dedup_papers

        papers = [
            {"doi": "10.1234/abc", "title": "Paper A", "url": "http://a.com"},
            {"doi": "10.1234/abc", "title": "Paper A (duplicate)", "url": "http://a.com/dup"},
            {"doi": "10.5678/def", "title": "Paper B", "url": "http://b.com"},
        ]
        result = dedup_papers(papers)
        assert len(result) == 2

    def test_url_match_deduplicates(self):
        from src.utils import dedup_papers

        papers = [
            {"url": "http://same-url.com/paper", "title": "Same Paper"},
            {"url": "http://same-url.com/paper", "title": "Same Paper (dup)"},
        ]
        result = dedup_papers(papers)
        assert len(result) == 1

    def test_no_doi_no_url_keeps_all(self):
        from src.utils import dedup_papers

        papers = [
            {"title": "Paper A", "url": ""},
            {"title": "Paper B", "url": ""},
            {"title": "Paper C", "url": ""},
        ]
        result = dedup_papers(papers)
        assert len(result) == 3

    def test_empty_list(self):
        from src.utils import dedup_papers

        result = dedup_papers([])
        assert result == []


class TestCalculateCredibility:
    """Credibility score calculation (static method)."""

    def test_top_conference_gets_high_score(self):
        from src.services.pipeline import PipelineService

        score = PipelineService._calculate_credibility(
            venue="NeurIPS 2024", venue_type="conference", citation_count=50
        )
        assert score == 8.0

    def test_preprint_gets_low_score(self):
        from src.services.pipeline import PipelineService

        score = PipelineService._calculate_credibility(
            venue=None, venue_type="preprint", citation_count=0
        )
        assert score == 3.5

    def test_citation_cap_at_10(self):
        from src.services.pipeline import PipelineService

        score = PipelineService._calculate_credibility(
            venue=None, venue_type="conference", citation_count=500
        )
        assert score == 7.5

    def test_journal_default_score(self):
        from src.services.pipeline import PipelineService

        score = PipelineService._calculate_credibility(
            venue="Nature", venue_type="journal", citation_count=20
        )
        assert score == 6.1

    def test_unknown_venue_type(self):
        from src.services.pipeline import PipelineService

        score = PipelineService._calculate_credibility(
            venue=None, venue_type=None, citation_count=0
        )
        assert score == 4.5


class TestConfigValidation:
    """Config validators fail on missing secrets."""

    def test_empty_jwt_secret_raises(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "")
        monkeypatch.setenv("DATABASE_URL", "postgresql://test")

        from pydantic import ValidationError
        from src.config import Settings

        with pytest.raises(ValidationError) as exc:
            Settings(_env_file=None)
        assert "JWT_SECRET" in str(exc.value)

    def test_empty_database_url_raises(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "")

        from pydantic import ValidationError
        from src.config import Settings

        with pytest.raises(ValidationError) as exc:
            Settings(_env_file=None)
        assert "DATABASE_URL" in str(exc.value)

    def test_valid_config_passes(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET", "a" * 32)
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")

        from src.config import Settings

        settings = Settings(_env_file=None)
        assert settings.jwt_secret == "a" * 32
        assert settings.database_url == "postgresql://localhost/test"
