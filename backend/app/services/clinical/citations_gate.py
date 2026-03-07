from __future__ import annotations


def ensure_fuentes_per_section(md: str) -> tuple[str, list[str]]:
    """Deterministic quality gate: ensure each section has a 'Fuentes:' line.

    Rule:
    - For every H2 section ("## ") except "## Referencias", there must be at least one line starting
      with "Fuentes:" inside the first ~60 lines of that section.
    - If missing, insert: "Fuentes: (No encontrado / evidencia insuficiente)".

    Returns: (fixed_markdown, warnings)
    """

    if not md:
        return md, []

    lines = md.splitlines()
    warnings: list[str] = []

    h2_idxs = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    if not h2_idxs:
        return md, []

    def _has_fuentes(start: int, end: int) -> bool:
        for ln in lines[start:end]:
            if ln.strip().lower().startswith("fuentes:"):
                return True
        return False

    inserts: list[tuple[int, str]] = []

    for hi, idx in enumerate(h2_idxs):
        title = lines[idx].strip().lower()
        if title == "## referencias":
            continue

        next_idx = h2_idxs[hi + 1] if hi + 1 < len(h2_idxs) else len(lines)
        window_end = min(next_idx, idx + 60)
        if not _has_fuentes(idx + 1, window_end):
            inserts.append((idx + 1, "Fuentes: (No encontrado / evidencia insuficiente)"))
            warnings.append(f"Missing Fuentes line for section: {lines[idx].strip()}")

    if not inserts:
        return md, []

    for pos, text in sorted(inserts, key=lambda x: x[0], reverse=True):
        lines.insert(pos, text)
        if pos + 1 < len(lines) and lines[pos + 1].strip() != "":
            lines.insert(pos + 1, "")

    return "\n".join(lines), warnings
