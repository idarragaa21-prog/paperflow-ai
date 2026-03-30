"""Password reset code storage backed by Redis with in-memory fallback."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_REDIS_PREFIX = "reset_code:"
_TTL_SECONDS = 900  # 15 minutes

# In-memory fallback when Redis is unavailable
_fallback_codes: dict[str, str] = {}


def _get_redis():
    """Return a Redis client or None if unavailable."""
    try:
        from app.core.redis_conn import get_redis

        r = get_redis(for_worker=False)
        r.ping()
        return r
    except Exception:
        return None


def store_reset_code(email: str, code: str) -> None:
    """Store a password-reset code with a 15-minute TTL."""
    r = _get_redis()
    if r is not None:
        try:
            r.setex(f"{_REDIS_PREFIX}{email}", _TTL_SECONDS, code)
            return
        except Exception:
            logger.warning("Redis write failed for reset code, falling back to memory")
    _fallback_codes[email] = code


def get_reset_code(email: str) -> str | None:
    """Retrieve a stored reset code, or None if missing/expired."""
    r = _get_redis()
    if r is not None:
        try:
            val = r.get(f"{_REDIS_PREFIX}{email}")
            if val is not None:
                return val.decode() if isinstance(val, bytes) else val
            return None
        except Exception:
            logger.warning("Redis read failed for reset code, falling back to memory")
    return _fallback_codes.get(email)


def delete_reset_code(email: str) -> None:
    """Delete a stored reset code."""
    r = _get_redis()
    if r is not None:
        try:
            r.delete(f"{_REDIS_PREFIX}{email}")
            return
        except Exception:
            logger.warning("Redis delete failed for reset code, falling back to memory")
    _fallback_codes.pop(email, None)
