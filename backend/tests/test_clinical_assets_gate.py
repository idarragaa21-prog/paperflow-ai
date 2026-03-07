from __future__ import annotations

from app.services.clinical.assets_gate import ensure_assets_present


def test_assets_gate_adds_tables_and_figure_when_missing():
    md = """## Resumen ejecutivo
Fuentes: (No encontrado / evidencia insuficiente)

## Evaluación diagnóstica
Fuentes: (No encontrado / evidencia insuficiente)

## Referencias
1. x
"""

    fixed, warnings = ensure_assets_present(md, topic="Rodilla")
    assert "## Tablas rápidas" in fixed
    assert "```mermaid" in fixed
    assert len(warnings) >= 1


def test_assets_gate_noop_when_assets_present():
    md = """## Resumen ejecutivo
Fuentes: [PUBMED:PMID:1]

| A | B | Ref(s) |
|---|---|---|
| x | y | [PUBMED:PMID:1] |

```mermaid
flowchart TD
A-->B
```

## Referencias
1. x
"""

    fixed, warnings = ensure_assets_present(md, topic="X")
    assert fixed == md
    assert warnings == []
