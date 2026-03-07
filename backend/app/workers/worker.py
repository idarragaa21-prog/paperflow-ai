from __future__ import annotations

import logging
import os

# macOS: RQ uses fork() for work horses; some native libs can crash after fork
# when Objective-C runtime was initializing in another thread.
# This env var is commonly used for local dev to avoid those crashes.
os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")

import sys

from rq import Connection, SimpleWorker, Worker

from app.core.redis_conn import get_redis

logging.basicConfig(level=logging.INFO)


def main() -> None:
    redis = get_redis(for_worker=True)
    with Connection(redis):
        # macOS dev: avoid fork() work-horses (can crash with ObjC runtime).
        worker_cls = SimpleWorker if sys.platform == "darwin" else Worker
        worker = worker_cls(["research_console"])  # type: ignore[call-arg]
        worker.work()


if __name__ == "__main__":
    main()
