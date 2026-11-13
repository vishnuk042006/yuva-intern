import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

USERNAME_PATTERN = r"^[A-Za-z0-9_.-]{3,32}$"


def _check_password(value: str) -> str:
    if not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value):
        raise ValueError("Password must contain at least one letter and one digit")
    return value


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # blocks mass-assignment (e.g. "role": "admin")

    username: str = Field(pattern=USERNAME_PATTERN)
    password: str = Field(min_length=8, max_length=72)

    _pw = field_validator("password")(_check_password)


class AdminCreateUserIn(RegisterIn):
    role: Literal["admin", "staff", "user"] = "user"
    subscriber_id: int | None = Field(default=None, ge=1)


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=72)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    subscriber_id: int | None
