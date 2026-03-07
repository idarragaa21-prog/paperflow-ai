import pytest

from app.services.llm.presets import PIPELINE_PRESETS, USER_TIERS, get_preset, get_tier


def test_presets_exist():
    assert "ultrafast" in PIPELINE_PRESETS
    assert "premium_free" in PIPELINE_PRESETS
    assert "pro" in PIPELINE_PRESETS
    assert "enterprise" in PIPELINE_PRESETS


def test_tiers_exist():
    assert "free" in USER_TIERS
    assert "pro" in USER_TIERS
    assert "enterprise" in USER_TIERS


def test_get_preset_unknown_raises():
    with pytest.raises(KeyError):
        get_preset("nope")


def test_get_tier_unknown_raises():
    with pytest.raises(KeyError):
        get_tier("nope")
