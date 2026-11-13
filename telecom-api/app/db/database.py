from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool


def build_engine(url: str) -> Engine:
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///") or ":memory:" in url:
            kwargs["poolclass"] = StaticPool  # one shared in-memory DB (tests)
    else:
        kwargs.update(pool_size=20, max_overflow=20, pool_recycle=1800)
    return create_engine(url, **kwargs)
