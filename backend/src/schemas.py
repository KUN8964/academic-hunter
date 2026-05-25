"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    display_name: str | None = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    """User-updatable AI provider configuration. All fields optional — only sent fields are changed."""

    ai_api_key: str | None = None
    ai_base_url: str | None = None
    ai_model: str | None = None


class UserSettingsResponse(BaseModel):
    """User's AI settings. API key is masked for security (only last 4 chars shown)."""

    ai_api_key_masked: str | None = None
    ai_base_url: str | None = None
    ai_model: str | None = None

    @classmethod
    def from_user(cls, user) -> "UserSettingsResponse":
        masked = None
        if user.ai_api_key:
            masked = "sk-..." + user.ai_api_key[-4:] if len(user.ai_api_key) > 4 else "****"
        return cls(
            ai_api_key_masked=masked,
            ai_base_url=user.ai_base_url,
            ai_model=user.ai_model,
        )

    model_config = {"from_attributes": True}


# ── Topic Subscription ──

class TopicSubscriptionCreate(BaseModel):
    query_text: str


class TopicSubscriptionUpdate(BaseModel):
    query_text: str | None = None
    ai_keywords: list[str] | None = None
    status: str | None = None


class TopicSubscriptionResponse(BaseModel):
    id: str
    user_id: str
    query_text: str
    ai_keywords: list
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Researcher Subscription ──

class ResearcherSubscriptionCreate(BaseModel):
    researcher_name: str
    orcid: str | None = None
    s2_author_id: str | None = None
    dblp_pid: str | None = None


class ResearcherSubscriptionUpdate(BaseModel):
    researcher_name: str | None = None
    orcid: str | None = None
    s2_author_id: str | None = None
    dblp_pid: str | None = None
    ai_keywords: list[str] | None = None
    status: str | None = None


class ResearcherSubscriptionResponse(BaseModel):
    id: str
    user_id: str
    researcher_name: str
    orcid: str | None
    s2_author_id: str | None
    dblp_pid: str | None
    ai_keywords: list
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Paper ──

class PaperResponse(BaseModel):
    id: str
    source_type: str
    source_id: str
    doi: str | None
    title: str
    authors: list
    abstract: str | None
    url: str
    venue: str | None
    venue_type: str | None
    published_at: datetime | None
    ai_abstract_zh: str | None
    ai_tags: list
    ai_evaluation: str | None
    credibility_score: float | None
    citation_count: int | None

    model_config = {"from_attributes": True}


class PaperBriefItem(BaseModel):
    rank: int
    paper: PaperResponse
    credibility_score: float | None


# ── Daily Brief ──

class DailyBriefResponse(BaseModel):
    id: str
    user_id: str
    subscription_type: str
    subscription_id: str
    date: str
    papers: list
    generated_at: datetime

    model_config = {"from_attributes": True}


# ── Reports ──

class ResearchReportResponse(BaseModel):
    id: str
    user_id: str
    subscription_type: str
    subscription_id: str
    week_start: str
    content: str
    generated_at: datetime

    model_config = {"from_attributes": True}


# ── Search ──

class SearchRequest(BaseModel):
    query: str
    limit: int = 20


class SearchResponse(BaseModel):
    results: list[PaperResponse]
    total: int


# ── Onboarding ──

class OnboardingStartRequest(BaseModel):
    query_text: str
    # Optional AI provider config for public (no-login) usage
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = ""


class OnboardingStartResponse(BaseModel):
    ai_keywords: list[str]
    suggested_subfields: list[str]
    suggested_researchers: list[dict]  # [{name, orcid?, s2_author_id?}]


class OnboardingConfirmRequest(BaseModel):
    query_text: str
    ai_keywords: list[str]
    researcher_names: list[str] = []
