from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import sessionmaker

from app.controllers import auth, circles, complaints, health, plan_changes, plans, recharges, subscribers
from app.core.cache import Cache
from app.core.config import Settings
from app.core.errors import register_exception_handlers
from app.core.logging_config import configure_logging
from app.core.middleware import (
    BodySizeLimitMiddleware,
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)
from app.db.database import build_engine
from app.db.models import Base
from app.db.seed import seed

DESCRIPTION = """
Backend for a fictional Ahmedabad MVNO's prepaid **plan comparison & recharge** app.

* Authenticate with `POST /api/v1/auth/login`, then click **Authorize** and paste the token.
* Roles: `admin` (everything), `staff` (operations), `user` (own subscriber only).
* Plan browsing (`/plans`, `/circles`) is public.
"""


def create_app(settings: Settings | None = None, cache: Cache | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level)

    engine = build_engine(settings.database_url)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Base.metadata.create_all(engine)
        if settings.seed_on_startup:
            with session_factory() as session:
                seed(session, settings)
        yield
        engine.dispose()

    app = FastAPI(title=settings.app_name, version="1.0.0", description=DESCRIPTION, lifespan=lifespan)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.cache = cache or Cache.from_url(settings.redis_url, settings.cache_ttl_seconds)

    register_exception_handlers(app)

    # Starlette runs the LAST added middleware first (outermost).
    app.add_middleware(RateLimitMiddleware, general_limit=settings.rate_limit_per_minute, auth_limit=settings.auth_rate_limit_per_minute)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_middleware(SecurityHeadersMiddleware)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )
    app.add_middleware(RequestContextMiddleware)

    api = APIRouter(prefix="/api/v1")
    for module in (auth, circles, plans, subscribers, recharges, complaints, plan_changes):
        api.include_router(module.router)
    app.include_router(health.router)
    app.include_router(api)
    return app


app = create_app()
