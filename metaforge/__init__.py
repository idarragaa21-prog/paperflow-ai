"""MetaForge — a local-first meta-analysis engine for epidemiologists."""
from .service import analyze, analyze_csv, effects_from_rows
from .pooling import pool, egger_test
from .effects import effect_from_row, from_2x2, smd_hedges_g

__version__ = "0.1.0"
__all__ = [
    "analyze",
    "analyze_csv",
    "effects_from_rows",
    "pool",
    "egger_test",
    "effect_from_row",
    "from_2x2",
    "smd_hedges_g",
]
