from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from src.config import get_settings
from src.schemas.domain import Role, TokenPair, UserRecord


ALGORITHM = "HS256"


class TokenError(RuntimeError):
    pass


def create_token_pair(user: UserRecord) -> TokenPair:
    settings = get_settings()
    return TokenPair(
        access_token=create_token(
            user=user,
            token_type="access",
            expires_delta=timedelta(minutes=settings.jwt_access_token_minutes),
        ),
        refresh_token=create_token(
            user=user,
            token_type="refresh",
            expires_delta=timedelta(days=settings.jwt_refresh_token_days),
        ),
    )


def create_token(user: UserRecord, token_type: str, expires_delta: timedelta) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.username,
        "role": user.role.value,
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise TokenError("Invalid token") from exc

    if payload.get("typ") != expected_type:
        raise TokenError("Invalid token type")
    if not payload.get("sub"):
        raise TokenError("Missing token subject")
    if payload.get("role") not in {role.value for role in Role}:
        raise TokenError("Invalid token role")

    return payload

