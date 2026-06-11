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
    assert out["egger"] is not None
    assert len(out["studies"]) == 4


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


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "MetaForge" in r.text
