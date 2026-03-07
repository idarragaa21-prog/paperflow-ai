from uuid import uuid4

from app.services.billing.usage_tracker import UsageTracker


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
