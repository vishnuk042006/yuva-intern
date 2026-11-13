import logging
import re
import threading
import time
import uuid

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import error_body

logger = logging.getLogger("app.request")
_RID_RE = re.compile(r"^[A-Za-z0-9\-]{8,64}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Request id + structured access log + last-resort 500 handler."""

    async def dispatch(self, request, call_next):
        supplied = request.headers.get("x-request-id", "")
        rid = supplied if _RID_RE.match(supplied) else uuid.uuid4().hex
        request.state.request_id = rid
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled exception", extra={"request_id": rid})
            response = JSONResponse(
                status_code=500,
                content=error_body("internal_error", "An internal error occurred", rid),
            )
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = rid
        logger.info(
            "request",
            extra={
                "request_id": rid,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "client": request.client.host if request.client else None,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if not request.url.path.startswith(("/docs", "/redoc")):
            response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            response.headers.setdefault("Cache-Control", "no-store")
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects oversized bodies early (API4: unrestricted resource consumption)."""

    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > self.max_bytes:
            return JSONResponse(
                status_code=413,
                content=error_body(
                    "payload_too_large", "Request body too large", getattr(request.state, "request_id", None)
                ),
            )
        return await call_next(request)


class RateLimiter:
    """Fixed-window counter per key. In-memory (per process); for multi-replica
    deployments swap this for a Redis INCR/EXPIRE implementation."""

    def __init__(self, window_seconds: int = 60):
        self.window = window_seconds
        self._hits: dict[tuple[str, int], int] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int) -> tuple[bool, int]:
        now = time.time()
        window_id = int(now // self.window)
        retry_after = max(1, int(self.window - (now % self.window)))
        with self._lock:
            if len(self._hits) > 20000:
                self._hits = {k: v for k, v in self._hits.items() if k[1] >= window_id}
            count = self._hits.get((key, window_id), 0) + 1
            self._hits[(key, window_id)] = count
        return count <= limit, retry_after


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, general_limit: int, auth_limit: int):
        super().__init__(app)
        self.general_limit = general_limit
        self.auth_limit = auth_limit
        self.limiter = RateLimiter()

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path == "/health":
            return await call_next(request)
        # Do not trust X-Forwarded-For unless a trusted proxy sets it; use the socket peer.
        client = request.client.host if request.client else "unknown"
        is_auth = path.startswith(("/api/v1/auth/login", "/api/v1/auth/register"))
        bucket, limit = ("auth", self.auth_limit) if is_auth else ("api", self.general_limit)
        allowed, retry_after = self.limiter.hit(f"{client}:{bucket}", limit)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content=error_body(
                    "rate_limited", "Too many requests, slow down", getattr(request.state, "request_id", None)
                ),
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
