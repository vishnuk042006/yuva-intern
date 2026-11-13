from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import Pagination, get_current_user, get_db, pagination
from app.db.models import User
from app.schemas.common import Page
from app.schemas.transactions import PlanChangeIn, PlanChangeOut
from app.services.transaction_services import PlanChangeService

router = APIRouter(prefix="/plan-changes", tags=["Plan changes"])


@router.post("", response_model=PlanChangeOut, status_code=201, summary="Switch a subscriber to another plan")
def create_plan_change(data: PlanChangeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return PlanChangeService(db).create(user, data)


@router.get("", response_model=Page[PlanChangeOut], summary="Plan change history (own, or any for staff)")
def list_plan_changes(
    subscriber_id: int | None = Query(None, ge=1),
    page: Pagination = Depends(pagination),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return PlanChangeService(db).list(user, subscriber_id=subscriber_id, page=page.page, size=page.size)
