from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.controllers.deps import get_cache, get_db
from app.core.cache import Cache

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Liveness/readiness probe")
def health(response: Response, db: Session = Depends(get_db), cache: Cache = Depends(get_cache)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
        response.status_code = 503
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "cache_enabled": cache.enabled}
