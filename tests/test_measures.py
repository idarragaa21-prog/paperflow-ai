import math

import pytest

from metaforge.effects import (
    back_transform,
    correlation_z,
    effect_from_row,
    forward_transform,
    irr_from_person_time,
    proportion_logit,
)
from metaforge.pooling import pool


def test_irr_from_person_time():
    # rate1 = 20/1000, rate2 = 40/1000 -> IRR 0.5.
    e = irr_from_person_time(20, 1000, 40, 1000)
    assert round(math.exp(e.yi), 2) == 0.50
    assert e.measure == "IRR"


def test_proportion_logit_back_transform():
    e = proportion_logit(25, 100)
    assert e.measure == "PLOGIT"
    assert round(back_transform("PLOGIT", e.yi), 2) == 0.25


def test_proportion_boundary_correction():
    e = proportion_logit(0, 50)
    assert math.isfinite(e.yi)
    assert "correction" in (e.note or "")


def test_correlation_z_roundtrip():
    e = correlation_z(0.5, 100)
    assert round(back_transform("ZCOR", e.yi), 3) == 0.5
    assert round(e.vi, 5) == round(1 / 97, 5)


def test_back_forward_transform_inverse():
    for measure, val in [("OR", 0.75), ("PLOGIT", -0.4), ("ZCOR", 0.3), ("MD", 2.5)]:
        assert forward_transform(measure, back_transform(measure, val)) == pytest.approx(val, abs=1e-9)


def test_pool_proportion_runs():
    eff = [proportion_logit(e, 100, label=f"S{e}") for e in (10, 12, 9, 15)]
    r = pool(eff, model="random", tau2_method="REML")
    nat = r.natural()
    assert 0 < nat["estimate"] < 1


def test_hr_from_effect_ci_log_scale():
    from metaforge.effects import from_effect_and_ci
    from metaforge.pooling import pool
    eff = [from_effect_and_ci(0.78, 0.64, 0.95, measure="HR", label="A"),
           from_effect_and_ci(0.85, 0.70, 1.03, measure="HR", label="B")]
    r = pool(eff, model="fixed")
    assert r.log_scale
    assert 0.7 < r.natural()["estimate"] < 0.9


def test_unknown_measure_raises():
    with pytest.raises(ValueError, match="Unknown effect_measure"):
        effect_from_row({"study_label": "S", "effect_measure": "BOGUS", "yi": 0.1, "se": 0.1})


def test_subgroup_and_year_parsed_from_row():
    row = {"study_label": "S", "effect_measure": "OR", "subgroup": "A", "year": "2011",
           "a_events": 10, "b_non_events": 90, "c_events": 20, "d_non_events": 80}
    e = effect_from_row(row)
    assert e.subgroup == "A"
    assert e.sort_key == 2011.0
