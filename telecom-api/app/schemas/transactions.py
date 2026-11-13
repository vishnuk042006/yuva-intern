from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RechargeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subscriber_id: int = Field(ge=1)
    plan_id: int = Field(ge=1)
    payment_mode: Literal["upi", "card", "netbanking", "wallet"]


class RechargeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscriber_id: int
    plan_id: int
    amount_inr: int
    payment_mode: str
    status: str
    created_at: datetime
    valid_until: datetime


Category = Literal["network", "billing", "plan", "other"]
ComplaintStatus = Literal["open", "in_progress", "resolved", "closed"]
Channel = Literal["app", "call_centre"]


class ComplaintIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    subscriber_id: int = Field(ge=1)
    category: Category
    description: str = Field(min_length=10, max_length=1000)
    channel: Channel


class ComplaintStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: ComplaintStatus
    resolution_note: str | None = Field(default=None, max_length=500)


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscriber_id: int
    category: str
    description: str
    channel: str
    status: str
    duplicate_of_id: int | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class PlanChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    subscriber_id: int = Field(ge=1)
    to_plan_id: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=200)


class PlanChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscriber_id: int
    from_plan_id: int | None
    to_plan_id: int
    reason: str | None
    created_at: datetime


class UsageIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    recorded_on: date
    value: float = Field(gt=0, le=1_000_000)
    unit: str = Field(min_length=2, max_length=2, description="MB or GB (case-insensitive)")


class UsageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscriber_id: int
    recorded_on: date
    data_mb: float
    raw_value: float
    raw_unit: str


class UsageSummary(BaseModel):
    subscriber_id: int
    date_from: date | None
    date_to: date | None
    records: int
    total_mb: float
    total_gb: float
    items: list[UsageOut]
