from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


def make_page(items: list, total: int, page: int, size: int) -> dict:
    pages = -(-total // size) if total else 0
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}
