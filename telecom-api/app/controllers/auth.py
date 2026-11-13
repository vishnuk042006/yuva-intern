from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_current_user, get_db, get_settings, require_admin
from app.core.config import Settings
from app.db.models import User
from app.schemas.auth import AdminCreateUserIn, LoginIn, RegisterIn, TokenOut, UserOut
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=201, summary="Self-register an end-user account")
def register(data: RegisterIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    """Always creates a role=`user` account. Roles cannot be chosen by the caller."""
    return AuthService(db, settings).create_user(data.username, data.password, role="user")


@router.post("/login", response_model=TokenOut, summary="Log in and receive a JWT")
def login(data: LoginIn, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    token, expires_in = AuthService(db, settings).login(data.username, data.password)
    return TokenOut(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserOut, summary="Current user")
def me(user: User = Depends(get_current_user)):
    return user


@router.post(
    "/users",
    response_model=UserOut,
    status_code=201,
    summary="Create a user with any role (admin only)",
)
def create_user(
    data: AdminCreateUserIn,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: User = Depends(require_admin),
):
    return AuthService(db, settings).create_user(data.username, data.password, data.role, data.subscriber_id)
