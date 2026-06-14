import pytest
from fastapi.testclient import TestClient

from metaforge.api import app
from metaforge.effects import from_yi_se
from metaforge.extract import extract_tables, fields_for
from metaforge.metareg import bubble_svg, meta_regression

client = TestClient(app)


# ---- Meta-regression ----
def _eff(slope):
    xs = list(range(1, 9))
    return [from_yi_se(0.5 + slope * x, 0.08, measure="GEN", label=f"S{x}") for x in xs], xs


def test_meta_regression_recovers_slope():
    eff, xs = _eff(-0.1)
    reg = meta_regression(eff, xs, knapp_hartung=True)
    assert reg["slope"]["estimate"] == pytest.approx(-0.1, abs=0.01)
    assert reg["intercept"]["estimate"] == pytest.approx(0.5, abs=0.02)
    assert reg["slope"]["p_value"] < 0.01
    assert 0 <= reg["r2"] <= 100


def test_meta_regression_needs_three():
    with pytest.raises(ValueError):
        meta_regression([from_yi_se(0.1, 0.1), from_yi_se(0.2, 0.1)], [1, 2])


def test_meta_regression_constant_moderator_raises():
    eff, _ = _eff(0)
    with pytest.raises(ValueError, match="no varía"):
        meta_regression(eff, [3] * len(eff))


def test_bubble_svg():
    eff, xs = _eff(-0.1)
    reg = meta_regression(eff, xs)
    svg = bubble_svg(eff, xs, reg, "dose")
    assert svg.startswith("<svg") and "dose" in svg


def test_api_meta_regression_csv():
    csv = ("study_label,year,effect_measure,yi,se\n"
           "A,2010,GEN,0.50,0.08\nB,2012,GEN,0.30,0.08\nC,2014,GEN,0.10,0.08\nD,2016,GEN,-0.10,0.08\n")
    r = client.post("/meta-regression", json={"csv": csv, "moderator": "year"})
    assert r.status_code == 200
    body = r.json()
    assert body["slope"]["estimate"] < 0   # effect decreases with year
    assert "bubble_svg" in body


def test_api_meta_regression_bad_moderator():
    csv = "study_label,effect_measure,yi,se\nA,GEN,0.1,0.1\nB,GEN,0.2,0.1\nC,GEN,0.3,0.1\n"
    r = client.post("/meta-regression", json={"csv": csv, "moderator": "nope"})
    assert r.status_code == 400


# ---- Table extraction ----
def test_extract_tables_from_jats():
    xml = """<article><body><table-wrap><label>Table 1</label>
      <caption><p>Events by arm</p></caption>
      <table><thead><tr><th>Arm</th><th>Events</th><th>N</th></tr></thead>
      <tbody><tr><td>Drug</td><td>20</td><td>100</td></tr>
      <tr><td>Placebo</td><td>30</td><td>100</td></tr></tbody></table>
      </table-wrap></body></article>"""
    tables = extract_tables(xml)
    assert len(tables) == 1
    assert "Table 1" in tables[0] and "Drug | 20 | 100" in tables[0]


def test_fields_for_unchanged():
    assert fields_for("OR")[0] == "a_events"


# ---- Full-text screening ----
def test_api_fulltext_screen_no_fulltext():
    r = client.post("/screen/fulltext", json={"record": {"id": "1", "title": "x"},
                                              "inclusion": ["a"], "exclusion": ["b"]})
    assert r.status_code == 200
    body = r.json()
    assert body["phase"] == "fulltext"
    assert body["decision"] == "maybe"  # no pmcid -> no full text
