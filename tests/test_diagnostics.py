import math

import pytest

from metaforge import diagnostics as dg
from metaforge.effects import from_2x2, from_yi_se


def _doac():
    data = [
        ("ARISTOTLE", 212, 8908, 265, 8795, "Xa", 2011),
        ("ROCKET-AF", 269, 6989, 306, 6985, "Xa", 2011),
        ("RE-LY", 134, 5973, 199, 5823, "Thrombin", 2009),
        ("ENGAGE", 296, 6739, 337, 6695, "Xa", 2013),
    ]
    return [from_2x2(a, b, c, d, measure="OR", label=l, subgroup=s, sort_key=y)
            for (l, a, b, c, d, s, y) in data]


def test_leave_one_out_returns_one_row_per_study():
    loo = dg.leave_one_out(_doac(), model="random", tau2_method="REML")
    assert len(loo) == 4
    assert {r["omitted"] for r in loo} == {"ARISTOTLE", "ROCKET-AF", "RE-LY", "ENGAGE"}
    for r in loo:
        assert r["ci_low"] < r["estimate"] < r["ci_high"]


def test_leave_one_out_needs_three():
    assert dg.leave_one_out(_doac()[:2]) == []


def test_cumulative_orders_by_year():
    cum = dg.cumulative(_doac(), model="random", tau2_method="REML")
    assert len(cum) == 4
    assert cum[0]["k"] == 1 and cum[-1]["k"] == 4
    # First added is the earliest year (RE-LY, 2009).
    assert "RE-LY" in cum[0]["added"]


def test_subgroup_between_test():
    sg = dg.subgroup_analysis(_doac(), model="random", tau2_method="REML")
    assert sg is not None
    assert {g["subgroup"] for g in sg["groups"]} == {"Xa", "Thrombin"}
    assert sg["df"] == 1
    assert 0.0 <= sg["p_value"] <= 1.0


def test_subgroup_none_when_single_group():
    eff = [from_2x2(10, 90, 20, 80, label=f"S{i}", subgroup="A") for i in range(3)]
    assert dg.subgroup_analysis(eff) is None


def test_influence_baujat_coordinates():
    inf = dg.influence(_doac(), model="random", tau2_method="REML")
    assert len(inf) == 4
    for r in inf:
        assert r["baujat_x"] >= 0
        assert r["baujat_y"] >= 0


def test_trim_fill_symmetric_returns_zero():
    # Symmetric around 0 with matched precision -> no missing studies.
    eff = [from_yi_se(y, 0.2, label=f"S{i}") for i, y in enumerate([-0.4, -0.2, 0.0, 0.2, 0.4])]
    tf = dg.trim_and_fill(eff, model="fixed")
    assert tf["k0"] == 0
    assert tf["imputed"] == []


def test_trim_fill_detects_asymmetry():
    # Precise studies near zero, imprecise studies only positive -> left side missing.
    yi = [0.0, 0.05, -0.05, 0.6, 0.8, 1.0]
    se = [0.1, 0.1, 0.1, 0.3, 0.35, 0.45]
    eff = [from_yi_se(y, s, label=f"S{i}") for i, (y, s) in enumerate(zip(yi, se))]
    tf = dg.trim_and_fill(eff, model="random", tau2_method="DL")
    assert tf["k0"] >= 1
    assert tf["side"] == "left"
    assert len(tf["imputed"]) == tf["k0"]
    # Filling missing studies on the left pulls the estimate down.
    assert tf["adjusted_estimate"] <= tf["observed_estimate"] + 1e-9


def test_trim_fill_needs_three():
    assert dg.trim_and_fill(_doac()[:2]) is None
