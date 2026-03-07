from app.services.references_io import export_bibtex, export_ris, parse_bibtex_entries, parse_ris_entries


def test_parse_bibtex_and_export_roundtrip():
    content = """
@article{smith2024,
  title = {A paper about evidence synthesis},
  author = {Smith J and Doe A},
  journal = {Journal of Testing},
  year = {2024},
  doi = {10.1000/test}
}
""".strip()

    items = parse_bibtex_entries(content)
    assert len(items) == 1
    assert items[0]["title"] == "A paper about evidence synthesis"
    assert items[0]["authors"] == ["Smith J", "Doe A"]

    exported = export_bibtex(items)
    assert "@article{smith2024" in exported
    assert "doi = {10.1000/test}" in exported


def test_parse_ris_and_export():
    content = """
TY  - JOUR
AU  - Smith J
AU  - Doe A
TI  - A reproducible trial
JO  - Trials Journal
PY  - 2023
DO  - 10.2000/example
ER  -
""".strip()

    items = parse_ris_entries(content)
    assert len(items) == 1
    assert items[0]["publication_year"] == 2023
    assert items[0]["doi"] == "10.2000/example"

    exported = export_ris(items)
    assert "TY  - JOUR" in exported
    assert "TI  - A reproducible trial" in exported
