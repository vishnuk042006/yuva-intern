from sqlalchemy.orm import Session

from app.core.errors import ConflictError
from app.db.models import Circle
from app.repositories.catalog import CircleRepository
from app.schemas.circle import CircleIn


class CircleService:
    def __init__(self, db: Session):
        self.repo = CircleRepository(db)

    def list_all(self) -> list[Circle]:
        return self.repo.list_all()

    def create(self, data: CircleIn) -> Circle:
        if self.repo.get_by_code(data.code):
            raise ConflictError("A circle with this code already exists")
        return self.repo.add(Circle(**data.model_dump()))
