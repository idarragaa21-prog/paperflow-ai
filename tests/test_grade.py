from fastapi.testclient import TestClient

from metaforge.api import app
from metaforge.grade import auto_grade, certainty_label, compute_certainty
from metaforge.samples import EXAMPLES
from metaforge.service import analyze_csv

client = TestClient(app)


def _res():
    return analyze_csv(EXAMPLES["doac_or"]["csv"], model="random")


def test_compute_certainty_rct_full():
    c = compute_certainty("rct", {d: "none" for d in
                                  ["risk_of_bias", "inconsistency", "indirectness", "imprecision", "publication_bias"]})
    assert c["level"] == 4 and c["label"] == "Alta"


def test_compute_certainty_downgrades():
    c = compute_certainty("rct", {"risk_of_bias": "serious", "inconsistency": "very_serious",
                                  "indirectness": "none", "imprecision": "none", "publication_bias": "none"})
    assert c["level"] == 1  # 4 - 1 - 2 = 1


def test_observational_starts_low():
    c = compute_certainty("observational", {})
    assert c["level"] == 2 and c["label"] == "Baja"


def test_certainty_label_bounds():
    assert certainty_label(9) == "Alta"
    assert certainty_label(0) == "Muy baja"


def test_auto_grade_structure():
    g = auto_grade(_res(), design="rct")
    assert set(g["domains"]) >= {"risk_of_bias", "inconsistency", "imprecision"}
    assert 1 <= g["certainty"]["level"] <= 4
    # DOAC has a significant CI not crossing null -> imprecision not downgraded for crossing
    assert g["domains"]["imprecision"]["rating"] in ("none", "serious")


def test_auto_grade_rob_downgrades():
    rob = {"studies": ["A", "B"], "ratings": {"A": {"D1": "high", "D2": "high"}, "B": {"D1": "high"}}, "tool": "rob2"}
    g = auto_grade(_res(), design="rct", rob=rob)
    assert g["domains"]["risk_of_bias"]["rating"] == "serious"


def test_api_grade_auto_and_override():
    res = _res()
    r1 = client.post("/grade", json={"result": res, "design": "rct"})
    assert r1.status_code == 200 and "domains" in r1.json()
    r2 = client.post("/grade", json={"result": res, "design": "observational",
                                     "downgrades": {"risk_of_bias": "serious", "inconsistency": "none",
                                                    "indirectness": "none", "imprecision": "none", "publication_bias": "none"}})
    assert r2.json()["certainty"]["level"] == 1  # observational(2) - 1
