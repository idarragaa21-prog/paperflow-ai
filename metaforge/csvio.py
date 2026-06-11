"""Parse a pasted/uploaded CSV into effect rows."""
from __future__ import annotations

import csv
import io


STUDY_KEYS = {"study_label", "label", "authors", "year", "design", "doi", "pmid", "notes"}


def parse_csv(text: str) -> list[dict]:
    """Return a list of row dicts. Requires a header row with at least study_label."""
    text = text.strip()
    if not text:
        raise ValueError("Empty input")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("No header row found")
    headers = [h.strip().lower() for h in reader.fieldnames]
    if "study_label" not in headers and "label" not in headers:
        raise ValueError("CSV must include a 'study_label' column")

    rows: list[dict] = []
    for raw in reader:
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()}
        if not (row.get("study_label") or row.get("label")):
            continue
        rows.append(row)
    if not rows:
        raise ValueError("No data rows found")
    return rows
