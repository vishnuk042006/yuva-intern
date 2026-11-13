import json
import logging

logger = logging.getLogger("app.cache")


class Cache:
    """Thin Redis wrapper. If Redis is absent or failing, every call degrades to a
    cache miss so the API keeps working (cache is an optimisation, never a dependency)."""

    def __init__(self, client=None, ttl: int = 60):
        self.client = client
        self.ttl = ttl

    @classmethod
    def from_url(cls, url: str | None, ttl: int = 60) -> "Cache":
        if not url:
            return cls(None, ttl)
        try:
            import redis

            client = redis.Redis.from_url(
                url, decode_responses=True, socket_connect_timeout=0.3, socket_timeout=0.3
            )
            return cls(client, ttl)
        except Exception:  # pragma: no cover - depends on environment
            logger.warning("redis unavailable, caching disabled")
            return cls(None, ttl)

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def get_json(self, key: str):
        if not self.client:
            return None
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            logger.warning("cache get failed", exc_info=True)
            return None

    def set_json(self, key: str, value) -> None:
        if not self.client:
            return
        try:
            self.client.setex(key, self.ttl, json.dumps(value))
        except Exception:
            logger.warning("cache set failed", exc_info=True)

    def invalidate(self, prefix: str) -> None:
        if not self.client:
            return
        try:
            keys = list(self.client.scan_iter(match=prefix + "*"))
            if keys:
                self.client.delete(*keys)
        except Exception:
            logger.warning("cache invalidate failed", exc_info=True)
