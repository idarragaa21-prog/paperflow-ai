from __future__ import annotations

from redis import Redis

from app.config import settings


def get_redis(*, for_worker: bool = False) -> Redis:
    """Create a Redis client.

    Notes:
    - For API calls we want short timeouts to fail fast when Redis is down.
    - For RQ workers we MUST NOT set a low socket_timeout, otherwise the
      worker's pubsub/BLPOP loops can raise timeouts and quit.
    """

    if for_worker:
        return Redis.from_url(settings.REDIS_URL, socket_connect_timeout=3, socket_timeout=None)

    # API / request path: short timeouts
    return Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=2)


def redis_available() -> bool:
    try:
        r = get_redis(for_worker=False)
        return bool(r.ping())
    except Exception:
        return False
