from pydantic import BaseModel, ConfigDict, Field


class PlanIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=80)
    price_inr: int = Field(ge=1, le=100000)
    data_gb_per_day: float = Field(ge=0, le=100)
    validity_days: int = Field(ge=1, le=730)
    unlimited_calls: bool = True
    sms_per_day: int = Field(default=100, ge=0, le=1000)
    is_5g: bool = False
    ott_benefits: str | None = Field(default=None, max_length=200)
    circle_id: int | None = Field(default=None, ge=1)
    active: bool = True


class PlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=80)
    price_inr: int | None = Field(default=None, ge=1, le=100000)
    data_gb_per_day: float | None = Field(default=None, ge=0, le=100)
    validity_days: int | None = Field(default=None, ge=1, le=730)
    unlimited_calls: bool | None = None
    sms_per_day: int | None = Field(default=None, ge=0, le=1000)
    is_5g: bool | None = None
    ott_benefits: str | None = Field(default=None, max_length=200)
    circle_id: int | None = Field(default=None, ge=1)
    active: bool | None = None


class PlanOut(PlanIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PlanComparison(PlanOut):
    total_data_gb: float
    price_per_day: float
    price_per_gb: float | None


class PlanCompareOut(BaseModel):
    plans: list[PlanComparison]
    cheapest_plan_id: int
    best_value_plan_id: int | None  # lowest price per GB (plans with data only)
