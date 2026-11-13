from datetime import date

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, BadRequestError
from app.db.models import Subscriber, User
from app.repositories.catalog import CircleRepository, PlanRepository
from app.repositories.subscribers import SubscriberRepository
from app.schemas.common import make_page
from app.schemas.subscriber import SubscriberIn, SubscriberOut, SubscriberUpdate
from app.services.access import ensure_subscriber_access
from app.services.normalizers import reconcile_status


class SubscriberService:
    def __init__(self, db: Session):
        self.repo = SubscriberRepository(db)
        self.circles = CircleRepository(db)
        self.plans = PlanRepository(db)

    def _check_refs(self, circle_id: int | None, plan_id: int | None, effective_circle: int | None) -> None:
        if circle_id is not None and not self.circles.get(circle_id):
            raise NotFoundError("Circle")
        if plan_id is not None:
            plan = self.plans.get(plan_id)
            if not plan:
                raise NotFoundError("Plan")
            if plan.circle_id is not None and effective_circle is not None and plan.circle_id != effective_circle:
                raise ConflictError("Plan is not available in the subscriber's circle")

    def get(self, subscriber_id: int, user: User | None = None) -> Subscriber:
        if user is not None:
            ensure_subscriber_access(user, subscriber_id)
        sub = self.repo.get(subscriber_id)
        if not sub:
            raise NotFoundError("Subscriber")
        return sub

    def list(self, *, q, status, circle_id, plan_id, page, size) -> dict:
        items, total = self.repo.search(
            q=q, status=status, circle_id=circle_id, plan_id=plan_id, page=page, size=size
        )
        return make_page([SubscriberOut.model_validate(s) for s in items], total, page, size)

    def create(self, data: SubscriberIn) -> Subscriber:
        if self.repo.get_by_msisdn(data.msisdn):
            raise ConflictError("A subscriber with this mobile number already exists")
        self._check_refs(data.circle_id, data.plan_id, data.circle_id)
        payload = data.model_dump()
        if payload["status"] == "ported_out" and payload["ported_out_at"] is None:
            payload["ported_out_at"] = date.today()
        payload["status"], _ = reconcile_status(payload["status"], payload["ported_out_at"])
        return self.repo.add(Subscriber(**payload))

    def update(self, subscriber_id: int, data: SubscriberUpdate) -> Subscriber:
        sub = self.get(subscriber_id)
        changes = data.model_dump(exclude_unset=True)
        if not changes:
            raise BadRequestError("No fields to update")
        self._check_refs(changes.get("circle_id"), changes.get("plan_id"), changes.get("circle_id", sub.circle_id))
        for field, value in changes.items():
            if value is None and field not in ("email", "ported_out_at", "plan_id"):
                continue
            setattr(sub, field, value)
        if sub.status == "ported_out" and sub.ported_out_at is None:
            sub.ported_out_at = date.today()
        sub.status, _ = reconcile_status(sub.status, sub.ported_out_at)
        return self.repo.save(sub)

    def deactivate(self, subscriber_id: int) -> None:
        """DELETE is a soft delete (keeps recharge/complaint history for audit)."""
        sub = self.get(subscriber_id)
        sub.status = "inactive"
        self.repo.save(sub)
