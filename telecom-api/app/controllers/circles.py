from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_db, require_admin
from app.db.models import User
from app.schemas.circle import CircleIn, CircleOut
from app.services.circle_service import CircleService

router = APIRouter(prefix="/circles", tags=["Circles"])


@router.get("", response_model=list[CircleOut], summary="List telecom circles (public)")
def list_circles(db: Session = Depends(get_db)):
    return CircleService(db).list_all()


@router.post("", response_model=CircleOut, status_code=201, summary="Create a circle (admin)")
def create_circle(data: CircleIn, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return CircleService(db).create(data)
