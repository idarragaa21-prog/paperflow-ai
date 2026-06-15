"""A fully worked example review, loadable in one click for onboarding.

Builds a complete workspace state (question, protocol, data, analysis, GRADE,
PRISMA counts and a drafted manuscript) for the DOACs-vs-warfarin dataset, so a
first-time user can open the finished product and explore every step instead of
starting from a blank page.
"""
from __future__ import annotations

from .grade import auto_grade
from .manuscript import generate_manuscript
from .protocol import generate_protocol
from .samples import EXAMPLES
from .service import analyze

_QUESTION = ("¿En adultos con fibrilación auricular no valvular, los anticoagulantes "
             "orales directos (ACOD) reducen el ictus o la embolia sistémica frente a "
             "la warfarina?")


def demo_state() -> dict:
    csv = EXAMPLES["doac_or"]["csv"]
    result = analyze(_rows(csv), model="random", tau2_method="REML",
                     favours_low="ACOD", favours_high="warfarina")
    protocol = generate_protocol(_QUESTION, measure="OR", mode="local")["protocol"]
    grade = auto_grade(result, design="rct")
    manuscript = generate_manuscript(_QUESTION, result, protocol=protocol, mode="local")

    rob_ratings = {
        s["label"]: {"D1": "low", "D2": "low", "D3": "low", "D4": "low", "D5": "some"}
        for s in result["studies"]
    }
    prisma = {
        "identified_db": "1284", "identified_registers": "12", "duplicates": "286",
        "screened": "1010", "excluded_screen": "942", "sought": "68",
        "not_retrieved": "2", "fulltext_assessed": "66", "fulltext_excluded": "62",
        "included": str(result["k"]),
        "exclusion_reasons": "Diseño no aleatorizado (24); población no relevante (19); "
                             "desenlace no informado (12); datos no extraíbles (7)",
    }
    chosen = {
        "question": _QUESTION, "framework": "PICO", "measure": "OR",
        "population": "Adultos con fibrilación auricular no valvular",
        "exposure": "Anticoagulantes orales directos", "comparator": "Warfarina",
        "outcome": "Ictus o embolia sistémica",
        "design": "Ensayos clínicos aleatorizados",
        "finer": "Pregunta factible, relevante y con evidencia disponible (FINER).",
        "rationale": "Pregunta clásica con varios ECA grandes disponibles.",
    }
    return {
        "demo": True, "topic": "anticoagulantes orales directos vs warfarina en fibrilación auricular",
        "questionText": _QUESTION, "measure": "OR", "chosen": chosen, "questions": [chosen],
        "protocol": protocol, "csv": csv, "model": "random", "tau2": "REML", "kh": True,
        "flow": "ACOD", "fhigh": "warfarina", "result": result, "prisma": prisma,
        "robTool": "rob2", "robRatings": rob_ratings, "grade": grade,
        "manuscript": manuscript["sections"], "facts": manuscript["facts"], "step": 5,
    }


def _rows(csv: str) -> list[dict]:
    from .csvio import parse_csv
    return parse_csv(csv)
