"""Authentication router: register, login, profile."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..limiter import limiter
from ..models.models import User
from ..schemas import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    UserSettingsResponse,
    UserSettingsUpdate,
)
from ..services.auth import create_access_token, create_user, get_user_by_email, verify_password
from ..services.auth_middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, payload: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user and return a JWT token. Rate limit: 5/min per IP."""
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = await create_user(db, payload.email, payload.password, payload.display_name)
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email and password, return JWT token. Rate limit: 10/min per IP."""
    user = await get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get the current user's profile."""
    return current_user


@router.get("/settings", response_model=UserSettingsResponse)
async def get_settings(current_user: User = Depends(get_current_user)):
    """Get the current user's AI provider settings. API key is masked."""
    return UserSettingsResponse.from_user(current_user)


@router.put("/settings", response_model=UserSettingsResponse)
async def update_settings(
    payload: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's AI provider settings. Only set fields are changed."""
    if payload.ai_api_key is not None:
        current_user.ai_api_key = payload.ai_api_key if payload.ai_api_key else None
    if payload.ai_base_url is not None:
        current_user.ai_base_url = payload.ai_base_url if payload.ai_base_url else None
    if payload.ai_model is not None:
        current_user.ai_model = payload.ai_model if payload.ai_model else None

    await db.commit()
    await db.refresh(current_user)
    return UserSettingsResponse.from_user(current_user)
