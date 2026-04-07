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
from app.core.logger import logger


class _StructuredFormatter(logging.Formatter):
    """Emit stdlib log records in the same structured format as loguru."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        level = record.levelname.ljust(8)
        name = record.name
        msg = super().format(record)
        return f"{level} | {name} - {msg}"


def _configure_worker_logging() -> None:
    """Route stdlib logging (used by RQ and Redis) through our loguru handler."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_StructuredFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Silence noisy loggers
    logging.getLogger("rq.worker").setLevel(logging.INFO)
    logging.getLogger("redis").setLevel(logging.WARNING)


def main() -> None:
    _configure_worker_logging()
    logger.info("Worker starting up")

    redis = get_redis(for_worker=True)
    with Connection(redis):
        # macOS dev: avoid fork() work-horses (can crash with ObjC runtime).
        worker_cls = SimpleWorker if sys.platform == "darwin" else Worker
        worker = worker_cls(["research_console"])  # type: ignore[call-arg]
        logger.info("Worker listening on queue: research_console")
        worker.work()


if __name__ == "__main__":
    main()
