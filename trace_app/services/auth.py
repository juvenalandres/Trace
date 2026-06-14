import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from trace_app.config import settings
from trace_app.models.refresh_token import RefreshToken
from trace_app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token_raw(user_id: int) -> tuple[str, str]:
    """Returns (raw_token, family_id). Caller must store the token via store_refresh_token."""
    family_id = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "fid": family_id,
    }
    raw_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return raw_token, family_id


async def store_refresh_token(db: AsyncSession, user_id: int, raw_token: str, family_id: str) -> None:
    """Store a hashed refresh token in the database."""
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    rt = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        family_id=family_id,
        revoked=False,
        expires_at=expires_at,
    )
    db.add(rt)
    await db.commit()


class TokenReuseDetected(Exception):
    """Raised when a revoked refresh token is reused — indicates theft."""


async def rotate_refresh_token(
    db: AsyncSession, raw_token: str
) -> tuple[int, str, str]:
    """
    Validate a refresh token, revoke it, and issue a new pair.
    Returns (user_id, new_access_token, new_refresh_token).
    Raises TokenReuseDetected if the token was already revoked (reuse = theft).
    """
    # Decode the token to get user_id and family_id
    try:
        payload = jwt.decode(raw_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise ValueError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")

    user_id = int(payload["sub"])
    family_id = payload.get("fid")
    if not family_id:
        raise ValueError("Token missing family ID")

    # Look up the token hash in the DB
    token_hash = _hash_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        # Token not found in DB — could be an old token from before rotation was implemented,
        # or a forged token. Treat as invalid.
        raise ValueError("Refresh token not found or already rotated")

    if stored_token.revoked:
        # REUSE DETECTED: a revoked token is being reused.
        # Revoke the entire family to invalidate all tokens in the chain.
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked == False)
            .values(revoked=True)
        )
        await db.commit()
        raise TokenReuseDetected("Refresh token reuse detected — all tokens in family revoked")

    # Check expiry
    if stored_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        stored_token.revoked = True
        await db.commit()
        raise ValueError("Refresh token expired")

    # Revoke the current token
    stored_token.revoked = True
    await db.flush()

    # Issue new tokens with the same family_id
    new_access = create_access_token(user_id)

    new_expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    new_payload = {
        "sub": str(user_id),
        "exp": new_expire,
        "type": "refresh",
        "fid": family_id,
    }
    new_raw_refresh = jwt.encode(new_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    # Store the new refresh token
    new_hash = _hash_token(new_raw_refresh)
    new_rt = RefreshToken(
        user_id=user_id,
        token_hash=new_hash,
        family_id=family_id,
        revoked=False,
        expires_at=new_expire,
    )
    db.add(new_rt)
    await db.commit()

    return user_id, new_access, new_raw_refresh


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
