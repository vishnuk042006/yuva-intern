from dataclasses import dataclass

import jwt
from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.cache import Cache
from app.core.config import Settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.models import User

bearer_scheme = HTTPBearer(auto_error=False, description="Paste the access_token from POST /api/v1/auth/login")


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_cache(request: Request) -> Cache:
    return request.app.state.cache


def get_db(request: Request):
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise UnauthorizedError()
    try:
        payload = decode_token(creds.credentials, request.app.state.settings)
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise UnauthorizedError("Invalid or expired token")
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired token")
    return user  # role is read from the DB, never trusted from the token


def require_roles(*roles: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ForbiddenError()
        return user

    return dependency


require_admin = require_roles("admin")
require_staff = require_roles("admin", "staff")


@dataclass
class Pagination:
    page: int
    size: int


def pagination(
    page: int = Query(1, ge=1, le=1_000_000),
    size: int = Query(20, ge=1, le=100, description="Max 100"),
) -> Pagination:
    return Pagination(page, size)
