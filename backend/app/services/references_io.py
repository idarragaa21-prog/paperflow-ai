from __future__ import annotations

import re
from typing import Any


def _split_authors(raw: str | None) -> list[str]:
    if not raw:
        return []
    if " and " in raw:
        parts = raw.split(" and ")
    else:
        parts = re.split(r";|,", raw)
    return [part.strip() for part in parts if part.strip()]


def _extract_bibtex_fields(block: str) -> dict[str, str]:
    """Extract BibTeX fields from a single entry block.

    The simple regex approach fails for fields with nested braces (e.g.
    ``title = {{The} Great Study}``).  This parser walks the block character by
    character so it handles arbitrary nesting correctly (M14).
    """
    fields: dict[str, str] = {}
    # Skip the header line (@type{key,)
    start = block.find(",", block.find("{"))
    if start == -1:
        return fields
    content = block[start + 1:]

    i = 0
    n = len(content)
    while i < n:
        # Skip whitespace / commas between fields
        while i < n and content[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        # Read field name
        name_start = i
        while i < n and content[i] not in "= \t\r\n":
            i += 1
        field_name = content[name_start:i].strip().lower()
        if not field_name:
            break
        # Skip whitespace and '='
        while i < n and content[i] in " \t\r\n":
            i += 1
        if i >= n or content[i] != "=":
            break
        i += 1  # consume '='
        while i < n and content[i] in " \t\r\n":
            i += 1
        if i >= n:
            break
        # Read value: can be {…}, "…", or bare number
        value = ""
        if content[i] == "{":
            depth = 0
            j = i
            while j < n:
                if content[j] == "{":
                    depth += 1
                elif content[j] == "}":
                    depth -= 1
                    if depth == 0:
                        value = content[i + 1:j]
                        i = j + 1
                        break
                j += 1
            else:
                i = n
        elif content[i] == '"':
            j = i + 1
            while j < n and content[j] != '"':
                j += 1
            value = content[i + 1:j]
            i = j + 1
        else:
            # bare number or token (no braces/quotes)
            j = i
            while j < n and content[j] not in " \t\r\n,}":
                j += 1
            value = content[i:j]
            i = j
        # Strip inner brace wrappers used for case protection, e.g. {The}
        clean_value = re.sub(r"\{([^{}]*)\}", r"\1", value).strip()
        if field_name and clean_value:
            fields[field_name] = clean_value
    return fields


def parse_bibtex_entries(content: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for block in re.split(r"(?=@\w+\{)", content):
        block = block.strip()
        if not block:
            continue
        header_match = re.match(r"@(\w+)\{([^,]+),", block, re.DOTALL)
        if not header_match:
            continue
        entry_type = header_match.group(1).strip().lower()
        citation_key = header_match.group(2).strip()
        fields = _extract_bibtex_fields(block)
        title = fields.get("title", "").strip()
        if not title:
            continue
        entries.append(
            {
                "source_format": "bibtex",
                "entry_type": entry_type,
                "citation_key": citation_key,
                "title": title,
                "authors": _split_authors(fields.get("author")),
                "journal": fields.get("journal") or fields.get("booktitle"),
                "publication_year": int(fields["year"]) if str(fields.get("year") or "").isdigit() else None,
                "doi": fields.get("doi"),
                "pmid": fields.get("pmid"),
                "pmcid": fields.get("pmcid"),
                "language": fields.get("language"),
                "abstract_text": fields.get("abstract"),
                "raw_payload": fields,
            }
        )
    return entries


def parse_ris_entries(content: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] = {"authors": [], "raw_payload": {}}
    for line in content.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue
        if line.startswith("TY  -"):
            current = {"authors": [], "raw_payload": {"TY": line[6:].strip()}, "source_format": "ris"}
            continue
        if line.startswith("ER  -"):
            title = str(current.get("title") or "").strip()
            if title:
                entries.append(current)
            current = {"authors": [], "raw_payload": {}}
            continue
        if "  -" not in line:
            continue
        key, value = line.split("  -", 1)
        tag = key.strip()
        clean_value = value.strip()
        current.setdefault("raw_payload", {})[tag] = clean_value
        if tag == "TI" or tag == "T1":
            current["title"] = clean_value
        elif tag == "AU":
            current.setdefault("authors", []).append(clean_value)
        elif tag == "JO" or tag == "T2":
            current["journal"] = clean_value
        elif tag == "PY":
            year_match = re.search(r"\b(\d{4})\b", clean_value)
            current["publication_year"] = int(year_match.group(1)) if year_match else None
        elif tag == "DO":
            current["doi"] = clean_value
        elif tag == "AB":
            current["abstract_text"] = clean_value
        elif tag == "LA":
            current["language"] = clean_value
        elif tag == "AN":
            current["pmid"] = clean_value
    title = str(current.get("title") or "").strip()
    if title:
        entries.append(current)
    return entries


def export_bibtex(items: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, item in enumerate(items, start=1):
        key = item.get("citation_key") or f"paperflow_{index}"
        authors = " and ".join(item.get("authors") or [])
        fields = [
            f"  title = {{{item.get('title') or ''}}}",
            f"  author = {{{authors}}}",
        ]
        if item.get("journal"):
            fields.append(f"  journal = {{{item['journal']}}}")
        if item.get("publication_year"):
            fields.append(f"  year = {{{item['publication_year']}}}")
        if item.get("doi"):
            fields.append(f"  doi = {{{item['doi']}}}")
        if item.get("pmid"):
            fields.append(f"  pmid = {{{item['pmid']}}}")
        blocks.append("@article{" + str(key) + ",\n" + ",\n".join(fields) + "\n}")
    return "\n\n".join(blocks).strip() + ("\n" if blocks else "")


def export_ris(items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for item in items:
        lines.append("TY  - JOUR")
        for author in item.get("authors") or []:
            lines.append(f"AU  - {author}")
        lines.append(f"TI  - {item.get('title') or ''}")
        if item.get("journal"):
            lines.append(f"JO  - {item['journal']}")
        if item.get("publication_year"):
            lines.append(f"PY  - {item['publication_year']}")
        if item.get("doi"):
            lines.append(f"DO  - {item['doi']}")
        if item.get("pmid"):
            lines.append(f"AN  - {item['pmid']}")
        lines.append("ER  -")
        lines.append("")
    return "\n".join(lines).rstrip() + ("\n" if lines else "")
