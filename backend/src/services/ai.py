"""AI service — per-user configurable provider (DeepSeek, OpenAI-compatible)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx

from ..config import settings

if TYPE_CHECKING:
    from ..models.models import User


class AIService:
    """Calls an OpenAI-compatible chat API for paper scoring, summarization, and reports.

    Each instance is bound to a specific user's configuration.
    Falls back to server-level defaults when the user hasn't set their own.
    """

    def __init__(
        self,
        *,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
    ) -> None:
        self.api_key = api_key or settings.ai_api_key
        self.base_url = base_url or settings.ai_base_url
        self.model = model or settings.ai_model

    @classmethod
    def from_user(cls, user: User) -> AIService:
        """Create an AIService configured for a specific user."""
        return cls(
            api_key=user.ai_api_key or "",
            base_url=user.ai_base_url or "",
            model=user.ai_model or "",
        )

    @classmethod
    def default(cls) -> AIService:
        """Create an AIService using server-level defaults only."""
        return cls()

    async def _chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        """Send a chat completion request."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": 4096,
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _chat_json(self, system: str, user: str) -> dict:
        """Chat completion expecting a JSON response."""
        text = await self._chat(
            system=system + "\nYou MUST respond with valid JSON only, no other text.",
            user=user,
            temperature=0.1,
        )
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(text)

    # ── Public API ──────────────────────────────────────────────────────────

    async def score_paper(self, title: str, abstract: str, venue: str | None = None) -> dict:
        """Score a paper's relevance and importance on 0-10 scale."""
        system = """You are an expert research evaluator. Given a paper's title, abstract, and venue, 
rate its significance on a 0-10 scale. Return JSON: {"score": float, "reason": "brief reason in Chinese"}"""
        user = f"Title: {title}\nVenue: {venue or 'Unknown'}\nAbstract: {abstract[:2000]}"
        return await self._chat_json(system, user)

    async def summarize_paper_zh(self, title: str, abstract: str) -> dict:
        """Generate a Chinese summary and tags for a paper."""
        system = """You are a research assistant. Summarize the paper in Chinese and provide 3-5 Chinese tags.
Return JSON: {"summary_zh": "Chinese summary (~150 chars)", "tags": ["tag1", "tag2", ...]}"""
        user = f"Title: {title}\nAbstract: {abstract[:3000]}"
        return await self._chat_json(system, user)

    async def evaluate_paper(self, title: str, abstract: str) -> str:
        """Generate a critical evaluation of the paper in Chinese."""
        system = """You are a senior researcher. Evaluate this paper critically in Chinese.
Cover: 1) novelty, 2) methodology strengths/weaknesses, 3) relation to existing work, 4) practical impact.
Keep it under 300 Chinese characters. Be concise and insightful."""
        user = f"Title: {title}\nAbstract: {abstract[:3000]}"
        return await self._chat(system, user, temperature=0.5)

    async def generate_daily_brief(self, papers: list[dict], subscription_name: str, date: str) -> str:
        """Generate a daily brief markdown from scored papers."""
        papers_text = "\n\n".join(
            f"[{i+1}] {p['title']}\n    Authors: {', '.join(p.get('authors', []))}\n    Venue: {p.get('venue', 'Unknown')}\n    Score: {p.get('score', 'N/A')}\n    Summary: {p.get('summary_zh', 'N/A')}"
            for i, p in enumerate(papers)
        )
        system = f"""You are a research digest editor. Generate a daily brief in MARKDOWN for subscription '{subscription_name}' dated {date}.
Structure:
## 📋 {subscription_name} 每日简报 ({date})

### 🔴 高可信
(list papers with credibility ≥ 8.0, each with: title, authors, venue, 1-line AI summary)

### 🟡 中可信
(list papers with credibility 5.0-7.9)

### 🟢 待验证
(list papers with credibility < 5.0 or preprint)

Include total counts. Use Chinese throughout."""
        user = papers_text
        return await self._chat(system, user, temperature=0.4)

    async def generate_research_report(self, papers: list[dict], subscription_name: str, week_start: str) -> str:
        """Generate a weekly research report."""
        papers_text = "\n\n".join(
            f"- {p['title']} ({p.get('venue', 'Unknown')}, {p.get('published_at', 'N/A')})"
            for p in papers[:50]
        )
        system = f"""You are a research analyst. Generate a weekly research report in MARKDOWN for '{subscription_name}' (week starting {week_start}).
Structure:
## 📊 领域概览
(2-3 sentences on overall activity level, key themes)

## 🔥 热点方向
(3-5 emerging hot topics with brief descriptions)

## 📄 重点论文
(top 5 most significant papers with brief analysis)

## 👤 活跃研究者
(top 3-5 most active researchers in this dataset)

## 🏷️ 新兴子方向
(any emerging sub-fields detected)

Use Chinese throughout."""
        user = f"Papers this week:\n{papers_text}"
        return await self._chat(system, user, temperature=0.5)

    async def expand_topic(self, query_text: str) -> dict:
        """AI expands a user's natural language query into keywords, sub-fields, and suggested researchers."""
        system = """You are a research librarian. Given a natural language description of a research interest, 
expand it into search keywords (English, for paper search APIs), related sub-fields, and suggested key researchers in the area.
For each researcher, include a short 'field' in Chinese (2-4 characters max, e.g. 皮肤影像, NLP, 系统) describing their primary specialty.
Return JSON: {"keywords": ["kw1", "kw2", ...], "subfields": ["sub1", "sub2", ...], "researchers": [{"name": "...", "field": "皮肤影像", "orcid": "..." or null, "s2_author_id": "..." or null}]}"""
        user = query_text
        return await self._chat_json(system, user)
