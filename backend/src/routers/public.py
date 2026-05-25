"""Public endpoints — no authentication required.

These allow users to try the product without registering.
AI calls use the API key provided in the request body (nothing persisted server-side).
"""

from fastapi import APIRouter

from ..schemas import OnboardingStartRequest, OnboardingStartResponse
from ..services.ai import AIService

router = APIRouter(prefix="/public", tags=["public"])


@router.post("/onboarding/expand", response_model=OnboardingStartResponse)
async def public_expand(payload: OnboardingStartRequest):
    """Expand a research topic using the API key provided in the request.

    No account needed — key is used only for this request and not stored.
    """
    ai = AIService(
        api_key=payload.ai_api_key or "",
        base_url=payload.ai_base_url or "",
        model=payload.ai_model or "",
    )
    try:
        result = await ai.expand_topic(payload.query_text)
    except Exception:
        return OnboardingStartResponse(
            ai_keywords=[payload.query_text],
            suggested_subfields=[],
            suggested_researchers=[],
        )
    return OnboardingStartResponse(
        ai_keywords=result.get("keywords", []),
        suggested_subfields=result.get("subfields", []),
        suggested_researchers=result.get("researchers", []),
    )
