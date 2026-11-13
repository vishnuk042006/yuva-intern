from sqlalchemy import or_, select

from app.db.models import Subscriber
from app.repositories.base import BaseRepository, like_pattern


class SubscriberRepository(BaseRepository[Subscriber]):
    model = Subscriber

    def get_by_msisdn(self, msisdn: str) -> Subscriber | None:
        return self.db.scalar(select(Subscriber).where(Subscriber.msisdn == msisdn))

    def search(self, *, q=None, status=None, circle_id=None, plan_id=None, page=1, size=20):
        stmt = select(Subscriber)
        if q:
            pattern = like_pattern(q)
            stmt = stmt.where(
                or_(Subscriber.full_name.ilike(pattern, escape="\\"), Subscriber.msisdn.like(pattern, escape="\\"))
            )
        if status:
            stmt = stmt.where(Subscriber.status == status)
        if circle_id is not None:
            stmt = stmt.where(Subscriber.circle_id == circle_id)
        if plan_id is not None:
            stmt = stmt.where(Subscriber.plan_id == plan_id)
        stmt = stmt.order_by(Subscriber.id)
        return self.paginate(stmt, page, size)
