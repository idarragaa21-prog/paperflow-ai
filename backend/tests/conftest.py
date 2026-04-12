import asyncio
from collections.abc import Generator
import os

import pytest

os.environ.setdefault("PAPERFLOW_DISABLE_DOTENV", "1")
os.environ.setdefault("PAPERFLOW_DISABLE_PROMETHEUS", "1")
os.environ.setdefault("ENV", "development")
os.environ.setdefault("SECRET_KEY", "TEST_ONLY__paperflow_pytest_secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")
os.environ.setdefault("R_ENGINE_URL", "http://127.0.0.1:8010")
os.environ.setdefault("OPENCLAW_BASE_URL", "http://127.0.0.1:18789")
os.environ.setdefault("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")


@pytest.fixture(scope="session")
def event_loop_policy() -> Generator[asyncio.AbstractEventLoopPolicy, None, None]:
    """Provide the default asyncio event loop policy for the whole test session.

    This is the supported way (pytest-asyncio >= 0.23) to control event-loop
    behavior without redefining the deprecated `event_loop` fixture.
    """
    policy = asyncio.get_event_loop_policy()
    yield policy


@pytest.fixture(autouse=True)
def reset_auth_rate_limit_state(monkeypatch: pytest.MonkeyPatch):
    from app.services import auth_rate_limit

    monkeypatch.setattr(auth_rate_limit, "redis_available", lambda: False)
    auth_rate_limit._memory_windows.clear()
    yield
    auth_rate_limit._memory_windows.clear()
