from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import Pagination, get_current_user, get_db, pagination, require_staff
from app.db.models import User
from app.schemas.common import Page
from app.schemas.transactions import (
    Category,
    Channel,
    ComplaintIn,
    ComplaintOut,
    ComplaintStatus,
    ComplaintStatusUpdate,
)
from app.services.transaction_services import ComplaintService

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post(
    "",
    response_model=ComplaintOut,
    status_code=201,
    summary="Log a complaint (duplicates across app/call-centre are linked via duplicate_of_id)",
)
def create_complaint(data: ComplaintIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ComplaintService(db).create(user, data)


@router.get("", response_model=Page[ComplaintOut], summary="List complaints (own, or any for staff)")
def list_complaints(
    subscriber_id: int | None = Query(None, ge=1),
    status: ComplaintStatus | None = None,
    category: Category | None = None,
    channel: Channel | None = None,
    page: Pagination = Depends(pagination),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ComplaintService(db).list(
        user,
        subscriber_id=subscriber_id,
        status=status,
        category=category,
        channel=channel,
        page=page.page,
        size=page.size,
    )


@router.get("/{complaint_id}", response_model=ComplaintOut, summary="Get a complaint (own, or any for staff)")
def get_complaint(complaint_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return ComplaintService(db).get(user, complaint_id)


@router.patch(
    "/{complaint_id}/status", response_model=ComplaintOut, summary="Update complaint status (staff/admin)"
)
def update_complaint_status(
    complaint_id: int, data: ComplaintStatusUpdate, db: Session = Depends(get_db), _: User = Depends(require_staff)
):
    return ComplaintService(db).update_status(complaint_id, data)
