from __future__ import annotations

from datetime import datetime, timedelta, timezone
import threading

from app.core.redis_conn import get_redis, redis_available


class AuthRateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int):
        super().__init__("Too many authentication attempts")
        self.retry_after_seconds = retry_after_seconds


_lock = threading.Lock()
_memory_windows: dict[str, tuple[int, datetime]] = {}


def _window_key(scope: str, identifier: str) -> str:
    return f"auth_rl:{scope}:{identifier}"


def hit(scope: str, identifier: str, *, limit: int, window_seconds: int) -> None:
    key = _window_key(scope, identifier)
    if redis_available():
        redis = get_redis()
        count = int(redis.incr(key))
        if count == 1:
            redis.expire(key, window_seconds)
        if count > limit:
            ttl = int(redis.ttl(key) or window_seconds)
            raise AuthRateLimitExceeded(max(ttl, 1))
        return

    now = datetime.now(timezone.utc)
    with _lock:
        count, expires_at = _memory_windows.get(key, (0, now + timedelta(seconds=window_seconds)))
        if now >= expires_at:
            count = 0
            expires_at = now + timedelta(seconds=window_seconds)
        count += 1
        _memory_windows[key] = (count, expires_at)
        if count > limit:
            retry_after = int(max((expires_at - now).total_seconds(), 1))
            raise AuthRateLimitExceeded(retry_after)
