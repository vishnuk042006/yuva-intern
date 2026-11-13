from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    """Naive UTC timestamp (consistent across SQLite and PostgreSQL)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Circle(Base):
    __tablename__ = "circles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(4), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(60))


class Plan(Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("price_inr > 0", name="ck_plan_price_positive"),
        CheckConstraint("validity_days > 0", name="ck_plan_validity_positive"),
        Index("ix_plans_active_price", "active", "price_inr"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    price_inr: Mapped[int] = mapped_column(Integer)
    data_gb_per_day: Mapped[float] = mapped_column(Float, default=0)
    validity_days: Mapped[int] = mapped_column(Integer)
    unlimited_calls: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_per_day: Mapped[int] = mapped_column(Integer, default=100)
    is_5g: Mapped[bool] = mapped_column(Boolean, default=False)
    ott_benefits: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # NULL circle = national plan, otherwise only sold in that circle
    circle_id: Mapped[int | None] = mapped_column(ForeignKey("circles.id"), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Subscriber(Base):
    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(primary_key=True)
    msisdn: Mapped[str] = mapped_column(String(10), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    circle_id: Mapped[int] = mapped_column(ForeignKey("circles.id"), index=True)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(12), default="active", index=True)
    ported_out_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    balance_inr: Mapped[int] = mapped_column(Integer, default=0)
    plan_valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(72))
    role: Mapped[str] = mapped_column(String(10), default="user")  # admin | staff | user
    subscriber_id: Mapped[int | None] = mapped_column(ForeignKey("subscribers.id"), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Recharge(Base):
    __tablename__ = "recharges"
    __table_args__ = (Index("ix_recharges_sub_created", "subscriber_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    amount_inr: Mapped[int] = mapped_column(Integer)
    payment_mode: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(10), default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    valid_until: Mapped[datetime] = mapped_column(DateTime)


class Complaint(Base):
    __tablename__ = "complaints"
    __table_args__ = (Index("ix_complaints_sub_cat", "subscriber_id", "category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"))
    category: Mapped[str] = mapped_column(String(12))  # network | billing | plan | other
    description: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(12))  # app | call_centre
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)
    # Same issue logged twice (e.g. app + call centre) -> points at the original
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class PlanChange(Base):
    __tablename__ = "plan_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"), index=True)
    from_plan_id: Mapped[int | None] = mapped_column(ForeignKey("plans.id"), nullable=True)
    to_plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class UsageRecord(Base):
    """Data usage is ALWAYS stored normalised in MB; the raw value/unit as received
    (MB or GB mixed in source data) is kept for audit."""

    __tablename__ = "usage_records"
    __table_args__ = (Index("ix_usage_sub_date", "subscriber_id", "recorded_on"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    subscriber_id: Mapped[int] = mapped_column(ForeignKey("subscribers.id"))
    recorded_on: Mapped[date] = mapped_column(Date)
    data_mb: Mapped[float] = mapped_column(Float)
    raw_value: Mapped[float] = mapped_column(Float)
    raw_unit: Mapped[str] = mapped_column(String(4))
