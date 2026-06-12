"""MetaForge — a local-first meta-analysis engine for epidemiologists."""
from . import diagnostics
from .effects import (
    correlation_z,
    effect_from_row,
    from_2x2,
    irr_from_person_time,
    proportion_logit,
    smd_hedges_g,
)
from .pooling import egger_test, pool
from .service import analyze, analyze_csv, effects_from_rows

__version__ = "1.0.0"
__all__ = [
    "analyze",
    "analyze_csv",
    "effects_from_rows",
    "pool",
    "egger_test",
    "effect_from_row",
    "from_2x2",
    "irr_from_person_time",
    "smd_hedges_g",
    "proportion_logit",
    "correlation_z",
    "diagnostics",
]
