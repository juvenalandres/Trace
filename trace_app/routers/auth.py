import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from trace_app.config import settings
from trace_app.database import get_db
from trace_app.limiter import limiter
from trace_app.models.user import User
from trace_app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from trace_app.services.auth import (
    TokenReuseDetected,
    authenticate_user,
    create_access_token,
    create_refresh_token_raw,
    decode_token,
    hash_password,
    rotate_refresh_token,
    store_refresh_token,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

rate_limit = f"{settings.rate_limit_per_minute}/minute"

REFRESH_COOKIE = "refresh_token"
COOKIE_MAX_AGE = settings.jwt_refresh_token_expire_days * 86400


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=COOKIE_MAX_AGE,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/api/auth",
    )


@router.post("/register", response_model=TokenResponse)
@limiter.limit(rate_limit)
async def register(
    request: Request,
    response: Response,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    if not settings.allow_signup:
        raise HTTPException(
            status_code=403,
            detail="Registration is disabled. Contact the administrator.",
        )

    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # First user is admin by default
    user_count = await db.execute(select(func.count(User.id)))
    is_first_user = user_count.scalar() == 0

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        is_admin=is_first_user,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(user.id)
    raw_refresh, family_id = create_refresh_token_raw(user.id)
    await store_refresh_token(db, user.id, raw_refresh, family_id)

    _set_refresh_cookie(response, raw_refresh)

    return TokenResponse(access_token=access_token)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(rate_limit)
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.id)
    raw_refresh, family_id = create_refresh_token_raw(user.id)
    await store_refresh_token(db, user.id, raw_refresh, family_id)

    _set_refresh_cookie(response, raw_refresh)

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(rate_limit)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    raw_token = request.cookies.get(REFRESH_COOKIE)
    if not raw_token:
        raise HTTPException(status_code=401, detail="No refresh token")

    try:
        user_id, new_access, new_refresh = await rotate_refresh_token(db, raw_token)
    except TokenReuseDetected:
        logger.warning("Refresh token reuse detected — possible token theft")
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail="Token reuse detected. Please log in again.")
    except ValueError as e:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=401, detail=str(e))

    _set_refresh_cookie(response, new_refresh)

    return TokenResponse(access_token=new_access)


@router.post("/logout")
async def logout(response: Response):
    _clear_refresh_cookie(response)
    return {"ok": True}
