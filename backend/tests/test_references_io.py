from app.services.references_io import export_bibtex, export_ris, parse_bibtex_entries, parse_ris_entries
from app.api.references import _reference_item_payload


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


def test_reference_item_payload_keeps_parser_extras_out_of_orm_fields():
    entry = {
        "source_format": "bibtex",
        "entry_type": "article",
        "citation_key": "smith2024",
        "title": "A paper about evidence synthesis",
        "authors": ["Smith J", "Doe A"],
        "journal": "Journal of Testing",
        "publication_year": 2024,
        "doi": "10.1000/test",
        "raw_payload": {"title": "A paper about evidence synthesis"},
    }

    payload = _reference_item_payload(project_id="00000000-0000-0000-0000-000000000000", entry=entry)

    assert "entry_type" not in payload
    assert payload["raw_payload"]["parsed_extras"]["entry_type"] == "article"
    assert payload["citation_key"] == "smith2024"
