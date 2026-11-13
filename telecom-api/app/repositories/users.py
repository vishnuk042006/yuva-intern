from sqlalchemy import func, select

from app.db.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(func.lower(User.username) == username.lower()))

    def get_by_subscriber(self, subscriber_id: int) -> User | None:
        return self.db.scalar(select(User).where(User.subscriber_id == subscriber_id))
