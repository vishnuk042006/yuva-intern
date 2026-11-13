from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.controllers.deps import Pagination, get_cache, get_db, pagination, require_admin
from app.core.cache import Cache
from app.core.errors import BadRequestError
from app.db.models import User
from app.schemas.common import Page
from app.schemas.plan import PlanCompareOut, PlanIn, PlanOut, PlanUpdate
from app.services.plan_service import PlanService

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.get("", response_model=Page[PlanOut], summary="Search & filter active plans (public, Redis-cached)")
def list_plans(
    response: Response,
    q: str | None = Query(None, max_length=80, description="Name contains"),
    min_price: int | None = Query(None, ge=0),
    max_price: int | None = Query(None, ge=0),
    circle_id: int | None = Query(None, ge=1, description="Plans sellable in this circle (national + local)"),
    is_5g: bool | None = None,
    min_data_gb: float | None = Query(None, ge=0, description="Minimum GB per day"),
    validity_days: int | None = Query(None, ge=1),
    sort_by: Literal["price_inr", "data_gb_per_day", "validity_days", "name"] = "price_inr",
    order: Literal["asc", "desc"] = "asc",
    page: Pagination = Depends(pagination),
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
):
    filters = {
        k: v
        for k, v in dict(
            q=q,
            min_price=min_price,
            max_price=max_price,
            circle_id=circle_id,
            is_5g=is_5g,
            min_data_gb=min_data_gb,
            validity_days=validity_days,
        ).items()
        if v is not None
    }
    payload, hit = PlanService(db, cache).list_plans(filters, sort_by, order, page.page, page.size)
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return payload


@router.get("/compare", response_model=PlanCompareOut, summary="Compare 2-5 plans side by side (public)")
def compare_plans(
    ids: str = Query(..., description="Comma separated plan ids, e.g. 1,2,3", max_length=60),
    db: Session = Depends(get_db),
):
    try:
        plan_ids = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise BadRequestError("ids must be comma separated integers")
    return PlanService(db).compare(plan_ids)


@router.get("/{plan_id}", response_model=PlanOut, summary="Get a plan (public)")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    return PlanService(db).get(plan_id)


@router.post("", response_model=PlanOut, status_code=201, summary="Create a plan (admin)")
def create_plan(
    data: PlanIn, db: Session = Depends(get_db), cache: Cache = Depends(get_cache), _: User = Depends(require_admin)
):
    return PlanService(db, cache).create(data)


@router.put("/{plan_id}", response_model=PlanOut, summary="Update a plan (admin, partial fields allowed)")
def update_plan(
    plan_id: int,
    data: PlanUpdate,
    db: Session = Depends(get_db),
    cache: Cache = Depends(get_cache),
    _: User = Depends(require_admin),
):
    return PlanService(db, cache).update(plan_id, data)


@router.delete("/{plan_id}", status_code=204, summary="Retire a plan (admin, soft delete)")
def delete_plan(
    plan_id: int, db: Session = Depends(get_db), cache: Cache = Depends(get_cache), _: User = Depends(require_admin)
):
    PlanService(db, cache).deactivate(plan_id)
    return Response(status_code=204)
