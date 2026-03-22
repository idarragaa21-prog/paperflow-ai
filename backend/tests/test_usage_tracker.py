"""Tests for the DB-backed UsageTracker."""
from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.services.billing.usage_tracker import UsageTracker

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_session() -> tuple:
    """Create a fresh in-memory SQLite engine with all tables."""
    import app.models  # noqa: F401 — registers all models
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_maker


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_usage_tracker_records_and_limits():
    engine, session_maker = await _make_session()
    try:
        async with session_maker() as db:
            t = UsageTracker(db=db)
            user_id = uuid4()

            # free tier = 10/month (from presets)
            for _ in range(10):
                await t.record_generation(
                    user_id=user_id,
                    sheet_id=uuid4(),
                    preset="premium_free",
                    models_used=["openclaw/default"],
                    tokens_total=100,
                    cost_usd=0.0,
                    duration_sec=1.2,
                )
            await db.commit()

            res = await t.can_generate(user_id=user_id, tier="free")
            assert res.ok is False
            assert "Limit reached" in res.message

            stats = await t.get_stats(user_id=user_id)
            assert stats["sheets_this_month"] == 10
            assert stats["tokens_this_month"] == 1000
            assert len(stats["recent"]) == 10
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_usage_tracker_unlimited_enterprise():
    engine, session_maker = await _make_session()
    try:
        async with session_maker() as db:
            t = UsageTracker(db=db)
            res = await t.can_generate(user_id=uuid4(), tier="enterprise")
            assert res.ok is True
            assert res.message == "unlimited"
    finally:
        await engine.dispose()
