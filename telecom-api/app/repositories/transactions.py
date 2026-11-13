from datetime import date, datetime, time

from sqlalchemy import select

from app.db.models import Complaint, PlanChange, Recharge, UsageRecord
from app.repositories.base import BaseRepository


def _day_start(d: date) -> datetime:
    return datetime.combine(d, time.min)


def _day_end(d: date) -> datetime:
    return datetime.combine(d, time.max)


class RechargeRepository(BaseRepository[Recharge]):
    model = Recharge

    def search(self, *, subscriber_id=None, status=None, date_from=None, date_to=None, page=1, size=20):
        stmt = select(Recharge)
        if subscriber_id is not None:
            stmt = stmt.where(Recharge.subscriber_id == subscriber_id)
        if status:
            stmt = stmt.where(Recharge.status == status)
        if date_from:
            stmt = stmt.where(Recharge.created_at >= _day_start(date_from))
        if date_to:
            stmt = stmt.where(Recharge.created_at <= _day_end(date_to))
        return self.paginate(stmt.order_by(Recharge.created_at.desc(), Recharge.id.desc()), page, size)


class ComplaintRepository(BaseRepository[Complaint]):
    model = Complaint

    def search(self, *, subscriber_id=None, status=None, category=None, channel=None, page=1, size=20):
        stmt = select(Complaint)
        if subscriber_id is not None:
            stmt = stmt.where(Complaint.subscriber_id == subscriber_id)
        if status:
            stmt = stmt.where(Complaint.status == status)
        if category:
            stmt = stmt.where(Complaint.category == category)
        if channel:
            stmt = stmt.where(Complaint.channel == channel)
        return self.paginate(stmt.order_by(Complaint.created_at.desc(), Complaint.id.desc()), page, size)

    def open_candidates(self, subscriber_id: int, category: str) -> list[Complaint]:
        """Original (non-duplicate) complaints still being worked on."""
        stmt = select(Complaint).where(
            Complaint.subscriber_id == subscriber_id,
            Complaint.category == category,
            Complaint.status.in_(("open", "in_progress")),
            Complaint.duplicate_of_id.is_(None),
        )
        return list(self.db.scalars(stmt))


class PlanChangeRepository(BaseRepository[PlanChange]):
    model = PlanChange

    def search(self, *, subscriber_id=None, page=1, size=20):
        stmt = select(PlanChange)
        if subscriber_id is not None:
            stmt = stmt.where(PlanChange.subscriber_id == subscriber_id)
        return self.paginate(stmt.order_by(PlanChange.created_at.desc(), PlanChange.id.desc()), page, size)


class UsageRepository(BaseRepository[UsageRecord]):
    model = UsageRecord

    def for_subscriber(self, subscriber_id: int, date_from=None, date_to=None) -> list[UsageRecord]:
        stmt = select(UsageRecord).where(UsageRecord.subscriber_id == subscriber_id)
        if date_from:
            stmt = stmt.where(UsageRecord.recorded_on >= date_from)
        if date_to:
            stmt = stmt.where(UsageRecord.recorded_on <= date_to)
        return list(self.db.scalars(stmt.order_by(UsageRecord.recorded_on, UsageRecord.id)))
