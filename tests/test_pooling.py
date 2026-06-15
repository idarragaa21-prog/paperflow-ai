import math

import pytest

from metaforge.effects import from_2x2, from_yi_se
from metaforge.pooling import egger_test, pool


def _doac_effects():
    data = [
        ("ARISTOTLE", 212, 8908, 265, 8795),
        ("ROCKET-AF", 269, 6989, 306, 6985),
        ("RE-LY", 134, 5973, 199, 5823),
        ("ENGAGE", 296, 6739, 337, 6695),
    ]
    return [from_2x2(a, b, c, d, measure="OR", label=lbl) for (lbl, a, b, c, d) in data]


def test_fixed_effect_pooled_or_is_protective():
    res = pool(_doac_effects(), model="fixed")
    nat = res.natural()
    assert 0.75 < nat["estimate"] < 0.85
    assert nat["ci_high"] < 1.0  # statistically significant benefit
    assert res.tau2 == 0.0


def test_random_effects_reml_runs_and_reports_heterogeneity():
    res = pool(_doac_effects(), model="random", tau2_method="REML", knapp_hartung=True)
    nat = res.natural()
    assert 0.7 < nat["estimate"] < 0.9
    assert res.i2 >= 0
    assert res.tau2 >= 0
    assert res.pi_low is not None and res.pi_high is not None
    assert res.knapp_hartung is True
    assert abs(sum(res.weights_pct) - 100.0) < 1e-6


def test_tau2_estimators_all_nonnegative():
    eff = _doac_effects()
    for method in ("DL", "PM", "REML"):
        res = pool(eff, model="random", tau2_method=method)
        assert res.tau2 >= 0


def test_homogeneous_studies_have_zero_heterogeneity():
    # Identical effects -> Q ~ 0, I2 = 0, tau2 = 0.
    eff = [from_yi_se(math.log(0.8), 0.1, measure="OR", label=f"S{i}") for i in range(5)]
    res = pool(eff, model="random", tau2_method="DL")
    assert res.i2 == pytest.approx(0.0, abs=1e-6)
    assert res.tau2 == pytest.approx(0.0, abs=1e-9)
    assert res.natural()["estimate"] == pytest.approx(0.8, abs=1e-3)


def test_known_two_study_inverse_variance():
    # Two studies, equal variance -> simple average on the log scale.
    eff = [from_yi_se(0.0, 0.2, measure="GEN", label="A"), from_yi_se(1.0, 0.2, measure="GEN", label="B")]
    res = pool(eff, model="fixed")
    assert res.estimate == pytest.approx(0.5, abs=1e-9)


def test_egger_runs():
    res = egger_test(_doac_effects())
    assert res.k == 4
    assert math.isfinite(res.p_value)


def test_egger_equal_standard_errors_does_not_crash():
    # All studies share one SE (e.g. equal n) -> Egger is undefined; must degrade.
    eff = [from_yi_se(y, 0.1, measure="GEN", label=f"S{i}") for i, y in enumerate([0.1, 0.2, 0.3, 0.15])]
    res = egger_test(eff)
    assert res.p_value == 1.0
    assert "No evaluable" in res.note


def test_empty_raises():
    with pytest.raises(ValueError):
        pool([])
