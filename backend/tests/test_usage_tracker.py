from uuid import uuid4

import pytest

from app.services.billing.usage_tracker import QuotaExceededError, UsageTracker


def test_usage_tracker_records_and_limits(tmp_path):
    path = tmp_path / "usage.json"
    t = UsageTracker(path=path)

    user_id = uuid4()

    # free tier = 10/month (from presets)
    for i in range(10):
        t.record_generation(
            user_id=user_id,
            sheet_id=uuid4(),
            preset="premium_free",
            models_used=["openclaw/default"],
            tokens_total=100,
            cost_usd=0.0,
            duration_sec=1.2,
        )

    res = t.can_generate(user_id=user_id, tier="free")
    assert res.ok is False
    assert "Limit reached" in res.message

    stats = t.get_stats(user_id=user_id)
    assert stats["sheets_this_month"] == 10
    assert stats["tokens_this_month"] == 1000
    assert len(stats["recent"]) == 10


def test_usage_tracker_unlimited_enterprise(tmp_path):
    t = UsageTracker(path=tmp_path / "usage.json")
    res = t.can_generate(user_id="abc", tier="enterprise")
    assert res.ok is True
    assert res.message == "unlimited"


def test_usage_tracker_tracks_llm_calls_and_summarizes_month(tmp_path):
    tracker = UsageTracker(path=tmp_path / "usage.json")
    user_id = uuid4()

    tracker.track_llm_call(user_id, "claude-sonnet-4-6", 1200, 400)
    tracker.track_llm_call(user_id, "gpt-4o", 600, 300)

    summary = tracker.get_usage_summary(user_id, period="month")
    history = tracker.get_usage_history(user_id, months=2)

    assert summary["calls_used"] == 2
    assert summary["tokens_in"] == 1800
    assert summary["tokens_out"] == 700
    assert summary["total_tokens"] == 2500
    assert {item["model"] for item in summary["models"]} == {"claude-sonnet-4-6", "gpt-4o"}
    assert len(history["months"]) == 2
    assert history["months"][0]["calls"] == 2


def test_usage_tracker_enforces_quota_after_limit(tmp_path):
    tracker = UsageTracker(path=tmp_path / "usage.json")
    user_id = uuid4()

    for _ in range(10):
        tracker.track_llm_call(user_id, "gpt-4o", 100, 20)

    with pytest.raises(QuotaExceededError):
        tracker.enforce_quota(user_id)
