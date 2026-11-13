from pydantic import BaseModel, ConfigDict, Field


class CircleIn(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    code: str = Field(pattern=r"^[A-Z]{2,4}$")
    name: str = Field(min_length=2, max_length=80)
    state: str = Field(min_length=2, max_length=60)


class CircleOut(CircleIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
