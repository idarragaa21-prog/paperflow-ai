"""Comprehensive extraction (fan-out) + Excel data-sheet building."""
from __future__ import annotations

import io

import metaforge.extract as ex
from metaforge.excel_export import extractions_to_xlsx


def _parts():
    return {
        "narrative": "Ensayo aleatorizado en España. La mortalidad fue menor con el fármaco.",
        "tables": [
            "Tabla 1 Basales | Edad | 60 | 61",
            "Tabla 2 Resultados | Muertes int 10/100 | Muertes ctrl 20/100",
        ],
        "captions": ["Figura 1. Curva de supervivencia."],
        "has_fulltext": True,
    }


def _fake_ai(prompt, timeout=150):
    if "CARACTERÍSTICAS" in prompt:
        return {
            "study": {"authors": "Smith", "year": "2020", "country": "España", "design": "ECA"},
            "population": {"description": "adultos", "total_n": 200, "age": "60"},
            "arms": [{"name": "Fármaco", "n": 100}, {"name": "Placebo", "n": 100}],
            "followup": "12 meses",
        }
    if "TABLA 1" in prompt:
        return {"outcomes": []}  # baseline table → nothing
    if "TABLA 2" in prompt:
        return {"outcomes": [{
            "name": "Mortalidad", "type": "binary", "timepoint": "12m",
            "intervention": {"events": 10, "n": 100}, "control": {"events": 20, "n": 100},
            "effect": {"measure": "OR", "value": 0.44, "ci_lower": 0.2, "ci_upper": 0.98},
            "source": "tabla 2"}]}
    # narrative call: a partial echo of the same outcome (should be deduped away)
    return {"outcomes": [{
        "name": "Mortalidad", "type": "binary", "timepoint": "12m",
        "intervention": {"events": 10}, "control": {}, "effect": {}, "source": "texto"}]}


def _patch(monkeypatch):
    monkeypatch.setattr(ex, "fetch_fulltext_full", lambda rec, **k: _parts())
    monkeypatch.setattr(ex, "ai_available", lambda: True)
    monkeypatch.setattr(ex, "run_claude_json", _fake_ai)


def test_extract_full_fans_out_and_merges(monkeypatch):
    _patch(monkeypatch)
    out = ex.extract_full({"authors": "Smith", "year": 2020, "pmcid": "PMC1", "doi": "10.x"},
                          mode="ai", max_workers=4)
    assert out["found"] is True
    assert out["note"] == ""
    d = out["data"]
    assert d["study"]["country"] == "España"
    assert d["population"]["total_n"] == 200
    assert len(d["arms"]) == 2
    # The partial narrative echo must be collapsed → exactly one outcome.
    assert len(d["outcomes"]) == 1
    o = d["outcomes"][0]
    assert o["intervention"]["events"] == 10 and o["control"]["events"] == 20
    assert o["effect"]["measure"] == "OR"


def test_extract_full_keeps_partial_on_error(monkeypatch):
    monkeypatch.setattr(ex, "fetch_fulltext_full", lambda rec, **k: _parts())
    monkeypatch.setattr(ex, "ai_available", lambda: True)

    def flaky(prompt, timeout=150):
        if "TABLA 1" in prompt:
            raise RuntimeError("timeout")  # one section fails
        return _fake_ai(prompt, timeout=timeout)

    monkeypatch.setattr(ex, "run_claude_json", flaky)
    out = ex.extract_full({"authors": "Smith", "year": 2020, "pmcid": "PMC1"}, mode="ai")
    # Other sections still produce data; the failure is reported but not fatal.
    assert out["found"] is True
    assert len(out["data"]["outcomes"]) == 1
    assert "parcial" in out["note"]


def test_extract_full_without_text():
    out = ex.extract_full({"authors": "X", "year": 2021}, mode="local")
    assert out["found"] is False
    assert out["data"] is None


def test_dedup_keeps_distinct_full_analyses():
    def mk(measure, value, events=None, n=None):
        return {"name": "Mort", "timepoint": "12m",
                "intervention": {"events": events, "n": n, "mean": None, "sd": None, "person_time": None},
                "control": {"events": None, "n": None, "mean": None, "sd": None, "person_time": None},
                "effect": {"measure": measure, "value": value, "ci_lower": value and value - 0.1,
                           "ci_upper": value and value + 0.1, "p": 0.01}}
    full_or = mk("OR", 0.44, events=10, n=100)
    full_or["control"] = {"events": 20, "n": 100, "mean": None, "sd": None, "person_time": None}
    adj_hr = mk("HR", 0.35)
    partial = {"name": "Mort", "timepoint": "12m",
               "intervention": {"events": 10, "n": None, "mean": None, "sd": None, "person_time": None},
               "control": {"events": None, "n": None, "mean": None, "sd": None, "person_time": None},
               "effect": {"measure": "", "value": None, "ci_lower": None, "ci_upper": None, "p": None}}
    kept = ex._dedup_outcomes([full_or, partial, adj_hr])
    measures = sorted(o["effect"]["measure"] for o in kept)
    assert measures == ["HR", "OR"]  # both full analyses kept, partial dropped


def test_excel_three_sheets_and_meta_mapping(monkeypatch):
    _patch(monkeypatch)
    out = ex.extract_full({"authors": "Smith", "year": 2020, "pmcid": "PMC1", "doi": "10.x"}, mode="ai")
    xlsx = extractions_to_xlsx([out])
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(xlsx))
    assert wb.sheetnames == ["Estudios", "Desenlaces", "Para meta-análisis"]
    meta = wb["Para meta-análisis"]
    rows = list(meta.iter_rows(values_only=True))
    assert rows[0][3] == "effect_measure"
    data_rows = [r for r in rows[1:] if r[0]]
    assert len(data_rows) == 1
    r = data_rows[0]
    # OR mapping: a=10,b=90,c=20,d=80
    assert (r[4], r[5], r[6], r[7]) == (10, 90, 20, 80)


def test_excel_handles_empty_extraction():
    xlsx = extractions_to_xlsx([{"data": None, "study_label": "X 2020"}])
    from openpyxl import load_workbook
    wb = load_workbook(io.BytesIO(xlsx))
    assert wb["Desenlaces"].max_row == 1  # header only
