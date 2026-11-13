from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import Pagination, get_current_user, get_db, pagination
from app.db.models import User
from app.schemas.common import Page
from app.schemas.transactions import RechargeIn, RechargeOut
from app.services.transaction_services import RechargeService

router = APIRouter(prefix="/recharges", tags=["Recharges"])


@router.post("", response_model=RechargeOut, status_code=201, summary="Recharge a subscriber with a plan")
def create_recharge(data: RechargeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return RechargeService(db).create(user, data)


@router.get("", response_model=Page[RechargeOut], summary="Recharge history (own, or any for staff)")
def list_recharges(
    subscriber_id: int | None = Query(None, ge=1),
    status: Literal["success", "failed"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Pagination = Depends(pagination),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return RechargeService(db).list(
        user,
        subscriber_id=subscriber_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page.page,
        size=page.size,
    )
