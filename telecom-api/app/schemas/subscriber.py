from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["active", "inactive", "suspended", "ported_out"]
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class SubscriberIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    msisdn: str = Field(pattern=r"^[6-9]\d{9}$", description="10-digit Indian mobile number")
    full_name: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, pattern=EMAIL_PATTERN, max_length=120)
    circle_id: int = Field(ge=1)
    plan_id: int | None = Field(default=None, ge=1)
    status: Status = "active"
    ported_out_at: date | None = None


class SubscriberUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, pattern=EMAIL_PATTERN, max_length=120)
    circle_id: int | None = Field(default=None, ge=1)
    plan_id: int | None = Field(default=None, ge=1)
    status: Status | None = None
    ported_out_at: date | None = None


class SubscriberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    msisdn: str
    full_name: str
    email: str | None
    circle_id: int
    plan_id: int | None
    status: str
    ported_out_at: date | None
    balance_inr: int
    plan_valid_until: datetime | None
    created_at: datetime
