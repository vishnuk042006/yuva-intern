"""Object-level authorisation (OWASP API1: BOLA). End users may only touch their own
subscriber; staff/admin may touch any."""
from app.core.errors import ForbiddenError
from app.db.models import User

STAFF_ROLES = ("admin", "staff")


def is_staff(user: User) -> bool:
    return user.role in STAFF_ROLES


def ensure_subscriber_access(user: User, subscriber_id: int) -> None:
    if is_staff(user):
        return
    if user.subscriber_id is None or user.subscriber_id != subscriber_id:
        raise ForbiddenError("You can only access your own subscriber data")


def scope_subscriber_filter(user: User, requested: int | None) -> int | None:
    """For list endpoints: end users are always pinned to their own subscriber id."""
    if is_staff(user):
        return requested
    if user.subscriber_id is None:
        raise ForbiddenError("This account is not linked to a subscriber")
    if requested is not None and requested != user.subscriber_id:
        raise ForbiddenError("You can only access your own subscriber data")
    return user.subscriber_id
