from __future__ import annotations


def ensure_evidence_profile_block(
    md: str,
    *,
    articles_available: bool,
    books_included: bool,
) -> tuple[str, list[str]]:
    """Insert a small evidence profile block at the top, if missing.

    Required phrasing (per user spec):
    - "Basado principalmente en literatura científica reciente" OR
    - "Apoyo conceptual de libros" (when applicable)

    Returns: (fixed_markdown, warnings)
    """

    if not md:
        return md, []

    lower = md.lower()
    if "perfil de evidencia" in lower:
        return md, []

    warnings: list[str] = []

    if articles_available:
        line1 = "**Perfil de evidencia:** Basado principalmente en literatura científica reciente (artículos PubMed/OA)."
    else:
        line1 = "**Perfil de evidencia:** No encontrado / evidencia insuficiente en literatura científica reciente."

    if books_included:
        line2 = "**Apoyo conceptual de libros:** Sí (solo definiciones/fisiopatología/contexto; no domina recomendaciones)."
    else:
        line2 = "**Apoyo conceptual de libros:** No."

    block = f"> {line1}\n> {line2}\n"

    warnings.append("Inserted evidence profile block.")
    return block + "\n" + md.lstrip(), warnings
