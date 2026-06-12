import pytest
from fastapi.testclient import TestClient

from metaforge.api import app
from metaforge.manuscript import SECTIONS, facts_summary, generate_manuscript, generate_section
from metaforge.protocol import generate_protocol
from metaforge.samples import EXAMPLES
from metaforge.service import analyze_csv

client = TestClient(app)


@pytest.fixture(scope="module")
def result():
    return analyze_csv(EXAMPLES["doac_or"]["csv"], model="random", tau2_method="REML")


# ---- Protocol ----
def test_protocol_local_structure():
    out = generate_protocol("¿El ejercicio reduce la presión arterial en adultos?", measure="MD", mode="local")
    p = out["protocol"]
    assert out["source"] == "local"
    assert p["inclusion_criteria"] and p["exclusion_criteria"]
    assert "mean_intervention" in p["extraction_fields"]


def test_protocol_extraction_matches_measure():
    assert "a_events" in generate_protocol("q", measure="OR", mode="local")["protocol"]["extraction_fields"]
    assert "r" in generate_protocol("q", measure="ZCOR", mode="local")["protocol"]["extraction_fields"]


def test_protocol_empty_raises():
    with pytest.raises(ValueError):
        generate_protocol("", mode="local")


def test_api_protocol(result):
    r = client.post("/protocol", json={"question": "¿X reduce Y?", "measure": "OR", "mode": "local"})
    assert r.status_code == 200
    assert r.json()["protocol"]["extraction_fields"]


# ---- Manuscript ----
def test_facts_summary_grounded(result):
    facts = facts_summary(result)
    assert "0.81" in facts          # the real pooled OR
    assert "I2 = 43%" in facts
    assert "Connolly" in facts


def test_manuscript_local_all_sections(result):
    out = generate_manuscript("¿Los DOAC reducen el ictus vs warfarina?", result, mode="local")
    assert out["source"] == "local"
    assert set(out["sections"]) == set(SECTIONS)
    # Results paragraph reports the real numbers.
    assert "0.81" in out["sections"]["results"]
    assert "4 estudios" in out["sections"]["results"]


def test_generate_section_local(result):
    out = generate_section("¿X?", result, "results", mode="local")
    assert out["section"] == "results"
    assert out["source"] == "local"
    assert "0.81" in out["text"]


def test_section_unknown_raises(result):
    with pytest.raises(ValueError):
        generate_section("¿X?", result, "bogus", mode="local")


def test_manuscript_needs_result():
    with pytest.raises(ValueError):
        generate_manuscript("¿X?", {}, mode="local")


def test_api_manuscript_local(result):
    r = client.post("/manuscript", json={"question": "¿X reduce Y?", "result": result, "mode": "local"})
    assert r.status_code == 200
    assert "results" in r.json()["sections"]


def test_api_section_local(result):
    r = client.post("/manuscript/section",
                    json={"question": "¿X?", "result": result, "section": "methods", "mode": "local"})
    assert r.status_code == 200
    assert r.json()["text"]
