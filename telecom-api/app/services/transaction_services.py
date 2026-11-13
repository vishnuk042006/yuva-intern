from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.db.models import Complaint, PlanChange, Recharge, UsageRecord, User, utcnow
from app.repositories.catalog import PlanRepository
from app.repositories.subscribers import SubscriberRepository
from app.repositories.transactions import (
    ComplaintRepository,
    PlanChangeRepository,
    RechargeRepository,
    UsageRepository,
)
from app.schemas.common import make_page
from app.schemas.transactions import (
    ComplaintIn,
    ComplaintOut,
    ComplaintStatusUpdate,
    PlanChangeIn,
    PlanChangeOut,
    RechargeIn,
    RechargeOut,
    UsageIn,
    UsageOut,
    UsageSummary,
)
from app.services.access import ensure_subscriber_access, scope_subscriber_filter
from app.services.normalizers import find_duplicate, normalize_usage_to_mb


class _Base:
    def __init__(self, db: Session):
        self.db = db
        self.subscribers = SubscriberRepository(db)
        self.plans = PlanRepository(db)

    def _subscriber(self, subscriber_id: int):
        sub = self.subscribers.get(subscriber_id)
        if not sub:
            raise NotFoundError("Subscriber")
        return sub

    def _plan(self, plan_id: int):
        plan = self.plans.get(plan_id)
        if not plan:
            raise NotFoundError("Plan")
        return plan


class RechargeService(_Base):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = RechargeRepository(db)

    def create(self, user: User, data: RechargeIn) -> Recharge:
        ensure_subscriber_access(user, data.subscriber_id)
        sub = self._subscriber(data.subscriber_id)
        plan = self._plan(data.plan_id)
        if sub.status != "active":
            raise ConflictError(f"Cannot recharge a {sub.status.replace('_', ' ')} subscriber")
        if not plan.active:
            raise ConflictError("This plan is no longer available")
        if plan.circle_id is not None and plan.circle_id != sub.circle_id:
            raise ConflictError("This plan is not available in the subscriber's circle")

        now = utcnow()
        base = now
        if sub.plan_id == plan.id and sub.plan_valid_until and sub.plan_valid_until > now:
            base = sub.plan_valid_until  # renewing the same plan stacks validity
        valid_until = base + timedelta(days=plan.validity_days)

        recharge = Recharge(
            subscriber_id=sub.id,
            plan_id=plan.id,
            amount_inr=plan.price_inr,
            payment_mode=data.payment_mode,
            status="success",  # payment gateway is simulated
            valid_until=valid_until,
        )
        self.db.add(recharge)
        sub.plan_id = plan.id
        sub.plan_valid_until = valid_until
        self.db.commit()
        self.db.refresh(recharge)
        return recharge

    def list(self, user: User, *, subscriber_id, status, date_from, date_to, page, size) -> dict:
        subscriber_id = scope_subscriber_filter(user, subscriber_id)
        if date_from and date_to and date_from > date_to:
            raise BadRequestError("date_from cannot be after date_to")
        items, total = self.repo.search(
            subscriber_id=subscriber_id, status=status, date_from=date_from, date_to=date_to, page=page, size=size
        )
        return make_page([RechargeOut.model_validate(r) for r in items], total, page, size)


class ComplaintService(_Base):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = ComplaintRepository(db)

    def create(self, user: User, data: ComplaintIn) -> Complaint:
        ensure_subscriber_access(user, data.subscriber_id)
        self._subscriber(data.subscriber_id)
        now = utcnow()
        original = find_duplicate(self.repo.open_candidates(data.subscriber_id, data.category), now)
        complaint = Complaint(**data.model_dump(), status="open", created_at=now, updated_at=now)
        if original:
            complaint.duplicate_of_id = original.id
        return self.repo.add(complaint)

    def get(self, user: User, complaint_id: int) -> Complaint:
        complaint = self.repo.get(complaint_id)
        if not complaint:
            raise NotFoundError("Complaint")
        ensure_subscriber_access(user, complaint.subscriber_id)
        return complaint

    def list(self, user: User, *, subscriber_id, status, category, channel, page, size) -> dict:
        subscriber_id = scope_subscriber_filter(user, subscriber_id)
        items, total = self.repo.search(
            subscriber_id=subscriber_id, status=status, category=category, channel=channel, page=page, size=size
        )
        return make_page([ComplaintOut.model_validate(c) for c in items], total, page, size)

    def update_status(self, complaint_id: int, data: ComplaintStatusUpdate) -> Complaint:
        complaint = self.repo.get(complaint_id)
        if not complaint:
            raise NotFoundError("Complaint")
        complaint.status = data.status
        if data.resolution_note is not None:
            complaint.resolution_note = data.resolution_note
        return self.repo.save(complaint)


class PlanChangeService(_Base):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = PlanChangeRepository(db)

    def create(self, user: User, data: PlanChangeIn) -> PlanChange:
        ensure_subscriber_access(user, data.subscriber_id)
        sub = self._subscriber(data.subscriber_id)
        new_plan = self._plan(data.to_plan_id)
        if sub.status != "active":
            raise ConflictError(f"Cannot change plan of a {sub.status.replace('_', ' ')} subscriber")
        if sub.plan_id == new_plan.id:
            raise ConflictError("Subscriber is already on this plan")
        if not new_plan.active:
            raise ConflictError("This plan is no longer available")
        if new_plan.circle_id is not None and new_plan.circle_id != sub.circle_id:
            raise ConflictError("This plan is not available in the subscriber's circle")

        change = PlanChange(
            subscriber_id=sub.id, from_plan_id=sub.plan_id, to_plan_id=new_plan.id, reason=data.reason
        )
        self.db.add(change)
        sub.plan_id = new_plan.id
        self.db.commit()
        self.db.refresh(change)
        return change

    def list(self, user: User, *, subscriber_id, page, size) -> dict:
        subscriber_id = scope_subscriber_filter(user, subscriber_id)
        items, total = self.repo.search(subscriber_id=subscriber_id, page=page, size=size)
        return make_page([PlanChangeOut.model_validate(c) for c in items], total, page, size)


class UsageService(_Base):
    def __init__(self, db: Session):
        super().__init__(db)
        self.repo = UsageRepository(db)

    def record(self, subscriber_id: int, data: UsageIn) -> UsageRecord:
        self._subscriber(subscriber_id)
        try:
            mb = normalize_usage_to_mb(data.value, data.unit)
        except ValueError as exc:
            raise BadRequestError(str(exc))
        record = UsageRecord(
            subscriber_id=subscriber_id,
            recorded_on=data.recorded_on,
            data_mb=mb,
            raw_value=data.value,
            raw_unit=data.unit.upper(),
        )
        return self.repo.add(record)

    def summary(self, user: User, subscriber_id: int, date_from, date_to) -> UsageSummary:
        ensure_subscriber_access(user, subscriber_id)
        self._subscriber(subscriber_id)
        if date_from and date_to and date_from > date_to:
            raise BadRequestError("date_from cannot be after date_to")
        rows = self.repo.for_subscriber(subscriber_id, date_from, date_to)
        total_mb = round(sum(r.data_mb for r in rows), 2)
        return UsageSummary(
            subscriber_id=subscriber_id,
            date_from=date_from,
            date_to=date_to,
            records=len(rows),
            total_mb=total_mb,
            total_gb=round(total_mb / 1024, 3),
            items=[UsageOut.model_validate(r) for r in rows],
        )
