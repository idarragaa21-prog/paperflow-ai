from fastapi.testclient import TestClient

from metaforge.api import app
from metaforge.service import analyze_csv

CSV = """study_label,effect_measure,a_events,b_non_events,c_events,d_non_events
A,OR,20,80,28,72
B,OR,24,76,30,70
C,OR,15,85,22,78
D,OR,30,70,34,66
"""

client = TestClient(app)


def test_analyze_csv_end_to_end():
    out = analyze_csv(CSV, model="random", tau2_method="REML")
    assert out["k"] == 4
    assert out["pooled"]["estimate"] > 0
    assert "<svg" in out["forest_svg"]
    assert "<svg" in out["funnel_svg"]
    assert "<svg" in out["loo_forest_svg"]
    assert "<svg" in out["baujat_svg"]
    assert out["egger"] is not None
    assert len(out["studies"]) == 4
    assert len(out["leave_one_out"]) == 4
    assert len(out["cumulative"]) == 4
    assert out["trim_fill"] is not None
    assert out["measure_label"] == "Odds ratio"


def test_subgroups_in_output():
    csv = (
        "study_label,subgroup,effect_measure,a_events,b_non_events,c_events,d_non_events\n"
        "A,G1,OR,20,80,28,72\nB,G1,OR,24,76,30,70\n"
        "C,G2,OR,15,85,22,78\nD,G2,OR,30,70,34,66\n"
    )
    out = analyze_csv(csv)
    assert out["subgroups"] is not None
    assert out["subgroups"]["df"] == 1


def test_mixed_measures_rejected():
    import pytest
    csv = "study_label,effect_measure,yi,se\nA,OR,0.1,0.1\nB,MD,0.2,0.1\n"
    with pytest.raises(ValueError, match="share one effect_measure"):
        analyze_csv(csv)


def test_api_health():
    assert client.get("/health").json()["status"] == "ok"


def test_api_analyze_csv():
    r = client.post("/analyze", json={"csv": CSV})
    assert r.status_code == 200
    body = r.json()
    assert body["k"] == 4
    assert body["forest_svg"].startswith("<svg")


def test_api_analyze_rows():
    rows = [
        {"study_label": "X", "effect_measure": "OR", "a_events": 10, "b_non_events": 90, "c_events": 18, "d_non_events": 82},
        {"study_label": "Y", "effect_measure": "OR", "a_events": 12, "b_non_events": 88, "c_events": 20, "d_non_events": 80},
        {"study_label": "Z", "effect_measure": "OR", "a_events": 8, "b_non_events": 92, "c_events": 15, "d_non_events": 85},
    ]
    r = client.post("/analyze", json={"rows": rows, "model": "fixed"})
    assert r.status_code == 200
    assert r.json()["model"] == "fixed"


def test_api_bad_request():
    r = client.post("/analyze", json={"csv": "not,a,valid\n1,2,3"})
    assert r.status_code == 400


def test_api_invalid_model():
    r = client.post("/analyze", json={"csv": CSV, "model": "bogus"})
    assert r.status_code == 400


def test_api_examples_listed_and_fetchable():
    listed = client.get("/examples").json()
    assert "doac_or" in listed
    ex = client.get("/examples/doac_or").json()
    assert "csv" in ex and "study_label" in ex["csv"]
    # And it actually analyses.
    r = client.post("/analyze", json={"csv": ex["csv"]})
    assert r.status_code == 200


def test_api_templates():
    kinds = client.get("/templates").json()["templates"]
    assert "2x2" in kinds
    r = client.get("/templates/2x2")
    assert r.status_code == 200
    assert "study_label" in r.text
    assert client.get("/templates/nope").status_code == 404


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "MetaForge" in r.text


def test_appjs_served():
    r = client.get("/app.js")
    assert r.status_code == 200
    assert "application/javascript" in r.headers["content-type"]
