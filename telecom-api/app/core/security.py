from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import Settings


def hash_password(password: str, rounds: int = 12) -> str:
    # bcrypt only looks at the first 72 bytes; schemas cap passwords at 72 chars.
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt(rounds=rounds)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], password_hash.encode())
    except ValueError:
        return False


def create_access_token(
    subject: str, settings: Settings, expires_delta: timedelta | None = None
) -> tuple[str, int]:
    delta = expires_delta if expires_delta is not None else timedelta(minutes=settings.access_token_minutes)
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "iat": now, "exp": now + delta}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(delta.total_seconds())


def decode_token(token: str, settings: Settings) -> dict:
    # Algorithms are pinned explicitly (prevents "alg: none" / algorithm confusion).
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "sub"]},
    )
