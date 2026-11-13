from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.controllers.deps import (
    Pagination,
    get_current_user,
    get_db,
    pagination,
    require_admin,
    require_staff,
)
from app.core.errors import ForbiddenError
from app.db.models import User
from app.schemas.common import Page
from app.schemas.subscriber import SubscriberIn, SubscriberOut, SubscriberUpdate
from app.schemas.transactions import UsageIn, UsageOut, UsageSummary
from app.services.subscriber_service import SubscriberService
from app.services.transaction_services import UsageService

router = APIRouter(prefix="/subscribers", tags=["Subscribers"])


@router.get("", response_model=Page[SubscriberOut], summary="Search subscribers (staff/admin)")
def list_subscribers(
    q: str | None = Query(None, max_length=80, description="Name or mobile number contains"),
    status: Literal["active", "inactive", "suspended", "ported_out"] | None = None,
    circle_id: int | None = Query(None, ge=1),
    plan_id: int | None = Query(None, ge=1),
    page: Pagination = Depends(pagination),
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    return SubscriberService(db).list(
        q=q, status=status, circle_id=circle_id, plan_id=plan_id, page=page.page, size=page.size
    )


@router.get("/me", response_model=SubscriberOut, summary="My subscriber profile")
def my_subscriber(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.subscriber_id is None:
        raise ForbiddenError("This account is not linked to a subscriber")
    return SubscriberService(db).get(user.subscriber_id)


@router.get("/{subscriber_id}", response_model=SubscriberOut, summary="Get a subscriber (own record or staff)")
def get_subscriber(subscriber_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return SubscriberService(db).get(subscriber_id, user)


@router.post("", response_model=SubscriberOut, status_code=201, summary="Create a subscriber (staff/admin)")
def create_subscriber(data: SubscriberIn, db: Session = Depends(get_db), _: User = Depends(require_staff)):
    return SubscriberService(db).create(data)


@router.put("/{subscriber_id}", response_model=SubscriberOut, summary="Update a subscriber (staff/admin)")
def update_subscriber(
    subscriber_id: int, data: SubscriberUpdate, db: Session = Depends(get_db), _: User = Depends(require_staff)
):
    return SubscriberService(db).update(subscriber_id, data)


@router.delete("/{subscriber_id}", status_code=204, summary="Deactivate a subscriber (admin, soft delete)")
def delete_subscriber(subscriber_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    SubscriberService(db).deactivate(subscriber_id)
    return Response(status_code=204)


@router.post(
    "/{subscriber_id}/usage",
    response_model=UsageOut,
    status_code=201,
    summary="Record data usage in MB or GB (staff/admin); stored normalised to MB",
)
def record_usage(
    subscriber_id: int, data: UsageIn, db: Session = Depends(get_db), _: User = Depends(require_staff)
):
    return UsageService(db).record(subscriber_id, data)


@router.get(
    "/{subscriber_id}/usage",
    response_model=UsageSummary,
    summary="Usage records + totals in MB and GB (own record or staff)",
)
def get_usage(
    subscriber_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return UsageService(db).summary(user, subscriber_id, date_from, date_to)
