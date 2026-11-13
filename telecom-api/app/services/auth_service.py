from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.repositories.subscribers import SubscriberRepository
from app.repositories.users import UserRepository

# Used to burn comparable CPU time when the username does not exist (anti user-enumeration).
_DUMMY_HASH = hash_password("dummy-password-1", rounds=4)


class AuthService:
    def __init__(self, db: Session, settings: Settings):
        self.users = UserRepository(db)
        self.subscribers = SubscriberRepository(db)
        self.settings = settings

    def create_user(self, username: str, password: str, role: str = "user", subscriber_id: int | None = None) -> User:
        if self.users.get_by_username(username):
            raise ConflictError("Username already taken")
        if subscriber_id is not None:
            if not self.subscribers.get(subscriber_id):
                raise NotFoundError("Subscriber")
            if self.users.get_by_subscriber(subscriber_id):
                raise ConflictError("Subscriber is already linked to a user")
        user = User(
            username=username,
            password_hash=hash_password(password, self.settings.bcrypt_rounds),
            role=role,
            subscriber_id=subscriber_id,
        )
        return self.users.add(user)

    def login(self, username: str, password: str) -> tuple[str, int]:
        user = self.users.get_by_username(username)
        ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
        if not user or not ok or not user.is_active:
            raise UnauthorizedError("Invalid username or password")
        return create_access_token(str(user.id), self.settings)
