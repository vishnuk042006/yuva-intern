from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


def like_pattern(term: str) -> str:
    """Escape LIKE wildcards so user input is matched literally."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class BaseRepository(Generic[T]):
    model: type[T]

    def __init__(self, db: Session):
        self.db = db

    def get(self, id_: int) -> T | None:
        return self.db.get(self.model, id_)

    def add(self, obj: T) -> T:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def save(self, obj: T) -> T:
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: T) -> None:
        self.db.delete(obj)
        self.db.commit()

    def paginate(self, stmt: Select, page: int, size: int) -> tuple[list[T], int]:
        total = self.db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
        items = list(self.db.scalars(stmt.offset((page - 1) * size).limit(size)))
        return items, total
