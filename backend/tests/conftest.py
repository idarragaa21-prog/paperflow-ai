import asyncio
from collections.abc import Generator
import os

import pytest

os.environ.setdefault("PAPERFLOW_DISABLE_DOTENV", "1")
os.environ.setdefault("PAPERFLOW_DISABLE_PROMETHEUS", "1")


@pytest.fixture(scope="session")
def event_loop_policy() -> Generator[asyncio.AbstractEventLoopPolicy, None, None]:
    """Provide the default asyncio event loop policy for the whole test session.

    This is the supported way (pytest-asyncio >= 0.23) to control event-loop
    behavior without redefining the deprecated `event_loop` fixture.
    """
    policy = asyncio.get_event_loop_policy()
    yield policy
