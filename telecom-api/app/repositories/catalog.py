from sqlalchemy import func, or_, select

from app.db.models import Circle, Plan
from app.repositories.base import BaseRepository, like_pattern


class CircleRepository(BaseRepository[Circle]):
    model = Circle

    def list_all(self) -> list[Circle]:
        return list(self.db.scalars(select(Circle).order_by(Circle.name)))

    def get_by_code(self, code: str) -> Circle | None:
        return self.db.scalar(select(Circle).where(Circle.code == code))


class PlanRepository(BaseRepository[Plan]):
    model = Plan
    SORTABLE = {
        "price_inr": Plan.price_inr,
        "data_gb_per_day": Plan.data_gb_per_day,
        "validity_days": Plan.validity_days,
        "name": Plan.name,
    }

    def get_by_name(self, name: str) -> Plan | None:
        return self.db.scalar(select(Plan).where(func.lower(Plan.name) == name.lower()))

    def get_many(self, ids: list[int]) -> list[Plan]:
        return list(self.db.scalars(select(Plan).where(Plan.id.in_(ids))))

    def search(
        self,
        *,
        q=None,
        min_price=None,
        max_price=None,
        circle_id=None,
        is_5g=None,
        min_data_gb=None,
        validity_days=None,
        active=True,
        sort_by="price_inr",
        order="asc",
        page=1,
        size=20,
    ):
        stmt = select(Plan)
        if active is not None:
            stmt = stmt.where(Plan.active == active)
        if q:
            stmt = stmt.where(Plan.name.ilike(like_pattern(q), escape="\\"))
        if min_price is not None:
            stmt = stmt.where(Plan.price_inr >= min_price)
        if max_price is not None:
            stmt = stmt.where(Plan.price_inr <= max_price)
        if circle_id is not None:  # plans sellable in that circle = national + circle-specific
            stmt = stmt.where(or_(Plan.circle_id.is_(None), Plan.circle_id == circle_id))
        if is_5g is not None:
            stmt = stmt.where(Plan.is_5g == is_5g)
        if min_data_gb is not None:
            stmt = stmt.where(Plan.data_gb_per_day >= min_data_gb)
        if validity_days is not None:
            stmt = stmt.where(Plan.validity_days == validity_days)
        column = self.SORTABLE[sort_by]
        stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Plan.id)
        return self.paginate(stmt, page, size)
