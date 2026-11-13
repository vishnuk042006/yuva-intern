import json

from sqlalchemy.orm import Session

from app.core.cache import Cache
from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.db.models import Plan
from app.repositories.catalog import CircleRepository, PlanRepository
from app.schemas.common import make_page
from app.schemas.plan import PlanComparison, PlanCompareOut, PlanIn, PlanOut, PlanUpdate

CACHE_PREFIX = "plans:"


class PlanService:
    def __init__(self, db: Session, cache: Cache | None = None):
        self.repo = PlanRepository(db)
        self.circles = CircleRepository(db)
        self.cache = cache

    # --- reads -------------------------------------------------------------------
    def list_plans(self, filters: dict, sort_by: str, order: str, page: int, size: int) -> tuple[dict, bool]:
        """Most-read endpoint -> cached in Redis. Returns (payload, cache_hit)."""
        if (
            filters.get("min_price") is not None
            and filters.get("max_price") is not None
            and filters["min_price"] > filters["max_price"]
        ):
            raise BadRequestError("min_price cannot be greater than max_price")

        key = CACHE_PREFIX + "list:" + json.dumps(
            {**filters, "sort_by": sort_by, "order": order, "page": page, "size": size}, sort_keys=True
        )
        if self.cache:
            cached = self.cache.get_json(key)
            if cached is not None:
                return cached, True

        items, total = self.repo.search(**filters, active=True, sort_by=sort_by, order=order, page=page, size=size)
        payload = make_page([PlanOut.model_validate(p).model_dump(mode="json") for p in items], total, page, size)
        if self.cache:
            self.cache.set_json(key, payload)
        return payload, False

    def get(self, plan_id: int) -> Plan:
        plan = self.repo.get(plan_id)
        if not plan:
            raise NotFoundError("Plan")
        return plan

    def compare(self, ids: list[int]) -> PlanCompareOut:
        if len(set(ids)) != len(ids):
            raise BadRequestError("Plan ids must be unique")
        if not 2 <= len(ids) <= 5:
            raise BadRequestError("Provide between 2 and 5 plan ids to compare")
        plans = {p.id: p for p in self.repo.get_many(ids)}
        missing = [i for i in ids if i not in plans]
        if missing:
            raise NotFoundError(f"Plan(s) {missing}")
        rows = []
        for pid in ids:
            p = plans[pid]
            total_gb = round(p.data_gb_per_day * p.validity_days, 2)
            rows.append(
                PlanComparison(
                    **PlanOut.model_validate(p).model_dump(),
                    total_data_gb=total_gb,
                    price_per_day=round(p.price_inr / p.validity_days, 2),
                    price_per_gb=round(p.price_inr / total_gb, 2) if total_gb > 0 else None,
                )
            )
        cheapest = min(rows, key=lambda r: r.price_inr)
        with_data = [r for r in rows if r.price_per_gb is not None]
        best_value = min(with_data, key=lambda r: r.price_per_gb) if with_data else None
        return PlanCompareOut(
            plans=rows, cheapest_plan_id=cheapest.id, best_value_plan_id=best_value.id if best_value else None
        )

    # --- writes ------------------------------------------------------------------
    def _check_circle(self, circle_id: int | None) -> None:
        if circle_id is not None and not self.circles.get(circle_id):
            raise NotFoundError("Circle")

    def _invalidate(self) -> None:
        if self.cache:
            self.cache.invalidate(CACHE_PREFIX)

    def create(self, data: PlanIn) -> Plan:
        if self.repo.get_by_name(data.name):
            raise ConflictError("A plan with this name already exists")
        self._check_circle(data.circle_id)
        plan = self.repo.add(Plan(**data.model_dump()))
        self._invalidate()
        return plan

    def update(self, plan_id: int, data: PlanUpdate) -> Plan:
        plan = self.get(plan_id)
        changes = data.model_dump(exclude_unset=True)
        if "name" in changes and changes["name"] is not None:
            existing = self.repo.get_by_name(changes["name"])
            if existing and existing.id != plan.id:
                raise ConflictError("A plan with this name already exists")
        if "circle_id" in changes:
            self._check_circle(changes["circle_id"])
        for field, value in changes.items():
            if value is None and field not in ("ott_benefits", "circle_id"):
                continue  # null is only meaningful for the nullable columns
            setattr(plan, field, value)
        plan = self.repo.save(plan)
        self._invalidate()
        return plan

    def deactivate(self, plan_id: int) -> None:
        """DELETE is a soft delete: existing subscribers/recharges keep their history."""
        plan = self.get(plan_id)
        plan.active = False
        self.repo.save(plan)
        self._invalidate()
