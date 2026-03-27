from __future__ import annotations

import os
import sys

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.config import settings
from app.core.redis_conn import redis_available


def rate_limit_key(request: Request) -> str:
    """Key para rate limiting.

    - Si autenticado: user_id (seteado por AuthMiddleware)
    - Si no: IP
    """

    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


# In development, Redis can be optional. If Redis is down, disable rate limiting to avoid breaking requests/tests.
_rate_limit_enabled = bool(
    settings.RATE_LIMIT_ENABLED
    and redis_available()
    and "PYTEST_CURRENT_TEST" not in os.environ
    and "pytest" not in sys.modules
)

limiter = Limiter(
    key_func=rate_limit_key,
    storage_uri=settings.REDIS_URL if _rate_limit_enabled else "memory://",
    enabled=_rate_limit_enabled,
)
