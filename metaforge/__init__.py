"""MetaForge — a local-first research workspace for epidemiologists:
question forging, protocol, meta-analysis and manuscript drafting."""
from . import diagnostics
from .docx_export import manuscript_docx
from .manuscript import generate_manuscript
from .prisma import prisma_svg
from .protocol import generate_protocol
from .questions import generate_questions
from .rob import rob_summary_svg
from .screen import screen_records
from .search import search_literature
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

__version__ = "2.10.0"
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
    "generate_questions",
    "generate_protocol",
    "generate_manuscript",
    "prisma_svg",
    "rob_summary_svg",
    "manuscript_docx",
    "search_literature",
    "screen_records",
]
