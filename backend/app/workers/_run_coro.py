"""Shared helpers re-used across all worker task modules."""
from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

_T = TypeVar("_T")
_worker_loop: asyncio.AbstractEventLoop | None = None
_worker_loop_lock = threading.Lock()


def run_coro(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run a coroutine in a stable event loop.

    On macOS we run RQ in SimpleWorker mode (no fork) to avoid ObjC fork crashes.
    Using asyncio.run() per job creates a new loop each time; combined with a global
    async SQLAlchemy engine/pool this can trigger:
    "Future attached to a different loop".
    """

    global _worker_loop

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # Expected: no running loop in sync RQ jobs.
        pass
    else:
        raise RuntimeError("run_coro() called from an async context")

    with _worker_loop_lock:
        if _worker_loop is None or _worker_loop.is_closed():
            _worker_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_worker_loop)

    return _worker_loop.run_until_complete(coro)
