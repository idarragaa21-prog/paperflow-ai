import math

import pytest

from metaforge.effects import (
    effect_from_row,
    from_2x2,
    from_effect_and_ci,
    mean_difference,
    smd_hedges_g,
)


def test_or_from_2x2_matches_known_value():
    # ARISTOTLE apixaban arm: OR ~ 0.79.
    e = from_2x2(212, 8908, 265, 8795, measure="OR")
    assert round(math.exp(e.yi), 2) == 0.79
    assert 0.08 < e.sei < 0.11


def test_rr_from_2x2():
    e = from_2x2(20, 80, 40, 60, measure="RR")
    # risk1 = 0.2, risk2 = 0.4 -> RR 0.5
    assert round(math.exp(e.yi), 2) == 0.50


def test_zero_cell_continuity_correction():
    e = from_2x2(0, 50, 8, 42, measure="OR")
    assert math.isfinite(e.yi) and math.isfinite(e.sei)
    assert "continuity" in (e.note or "")


def test_smd_hedges_g_sign_and_magnitude():
    # Intervention mean lower than control by ~1 pooled SD.
    e = smd_hedges_g(50, 10.0, 2.0, 50, 12.0, 2.0)
    assert e.yi < 0
    assert 0.8 < abs(e.yi) < 1.1


def test_mean_difference():
    e = mean_difference(30, 5.0, 1.0, 30, 3.0, 1.0)
    assert e.yi == pytest.approx(2.0)


def test_from_effect_and_ci_recovers_se():
    e = from_effect_and_ci(0.79, 0.66, 0.95, measure="OR")
    assert round(math.exp(e.yi), 2) == 0.79
    assert e.sei > 0


def test_effect_from_row_dispatch():
    e = from_2x2(10, 90, 20, 80)
    row = {"study_label": "S1", "effect_measure": "OR", "a_events": 10, "b_non_events": 90, "c_events": 20, "d_non_events": 80}
    assert effect_from_row(row).yi == pytest.approx(e.yi)


def test_effect_from_row_raises_without_data():
    with pytest.raises(ValueError):
        effect_from_row({"study_label": "S1", "effect_measure": "OR"})
