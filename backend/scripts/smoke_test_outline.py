from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running as a script without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.presentation_outline import PresentationOutline
from app.services.llm.factory import llm_provider


async def main() -> None:
    llm = llm_provider()

    print("Running generate_slide_outline (ensemble may take a few minutes)...")
    result = await llm.generate_slide_outline(
        topic="Fracturas pertrocantéricas: enfoque práctico",
        duration_minutes=45,
        audience="Residentes de ortopedia",
        papers=[
            {
                "id": "00000000-0000-0000-0000-000000000001",
                "title": "Dummy paper 1",
                "doi": "10.0000/dummy1",
                "pmid": "12345678",
                "journal": "J Dummy",
                "pub_year": 2020,
                "summary": "No reportado en el texto",
            },
            {
                "id": "00000000-0000-0000-0000-000000000002",
                "title": "Dummy paper 2",
                "doi": "10.0000/dummy2",
                "pmid": "87654321",
                "journal": "J Dummy",
                "pub_year": 2021,
                "summary": "No reportado en el texto",
            },
        ],
    )

    usage = result.get("usage") or {}
    passes = usage.get("passes") or []
    if passes:
        print("\nPasses:")
        for p in passes:
            print(
                f"- {p.get('name')}: model={p.get('model')} latency_ms={p.get('latency_ms')} "
                f"in={p.get('input_tokens')} out={p.get('output_tokens')} cost_usd={p.get('cost_usd')}"
            )

    outline = PresentationOutline.model_validate(result["outline"])
    print("\nSummary:")
    print("slide_count:", len(outline.slides))
    print("model:", result.get("model"))
    print("models_used:", usage.get("models_used"))
    print("total_cost_usd:", usage.get("total_cost_usd"))
    if usage.get("warnings"):
        print("warnings:")
        for w in usage["warnings"]:
            print("-", w)


if __name__ == "__main__":
    asyncio.run(main())
