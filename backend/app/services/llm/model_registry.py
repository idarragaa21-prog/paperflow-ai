from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class Provider(str, Enum):
    OLLAMA = "ollama"
    GROQ = "groq"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    TOGETHER = "together"
    OPENROUTER = "openrouter"
    CEREBRAS = "cerebras"
    SAMBANOVA = "sambanova"
    # Paid (optional)
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class TaskType(str, Enum):
    EXTRACT = "extract"
    STRUCTURE = "structure"
    CONTENT = "content"
    VALIDATE = "validate"
    POLISH = "polish"
    GENERAL = "general"


@dataclass
class ModelSpec:
    id: str
    provider: Provider
    api_model_name: str
    display_name: str

    context_window: int = 32768

    is_free: bool = True
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0

    quality_score: int = 85
    speed_score: int = 70
    reasoning_score: int = 80
    medical_score: int = 75
    code_score: int = 70

    best_for: list[TaskType] = field(default_factory=list)

    is_available: bool = True
    last_health_check: Optional[datetime] = None
    avg_latency_ms: Optional[float] = None

    real_quality_scores: list[float] = field(default_factory=list)
    total_calls: int = 0
    total_failures: int = 0


DEFAULT_MODELS_FEB_2026: list[ModelSpec] = [
    # === TIER GRATIS ===
    ModelSpec(
        id="ollama/qwen3:14b",
        provider=Provider.OLLAMA,
        api_model_name="qwen3:14b",
        display_name="Qwen 3 14B (Local)",
        context_window=32768,
        quality_score=88,
        speed_score=75,
        medical_score=82,
        code_score=85,
        best_for=[TaskType.EXTRACT, TaskType.STRUCTURE],
    ),
    ModelSpec(
        id="ollama/qwen3:32b",
        provider=Provider.OLLAMA,
        api_model_name="qwen3:32b",
        display_name="Qwen 3 32B (Local)",
        context_window=65536,
        quality_score=92,
        speed_score=55,
        medical_score=88,
        code_score=88,
        best_for=[TaskType.CONTENT, TaskType.VALIDATE],
    ),
    ModelSpec(
        id="ollama/llama4:70b",
        provider=Provider.OLLAMA,
        api_model_name="llama4:70b-q4",
        display_name="Llama 4 70B Q4 (Local)",
        context_window=131072,
        quality_score=93,
        speed_score=40,
        medical_score=90,
        code_score=85,
        best_for=[TaskType.CONTENT],
    ),
    ModelSpec(
        id="groq/llama-4-scout-17b",
        provider=Provider.GROQ,
        api_model_name="meta-llama/llama-4-scout-17b-16e-instruct",
        display_name="Llama 4 Scout 17B (Groq)",
        context_window=131072,
        quality_score=89,
        speed_score=95,
        medical_score=83,
        code_score=82,
        best_for=[TaskType.EXTRACT, TaskType.STRUCTURE],
    ),
    ModelSpec(
        id="groq/llama-4-maverick-17b",
        provider=Provider.GROQ,
        api_model_name="meta-llama/llama-4-maverick-17b-128e-instruct",
        display_name="Llama 4 Maverick 17B (Groq)",
        context_window=131072,
        quality_score=91,
        speed_score=90,
        medical_score=86,
        code_score=84,
        best_for=[TaskType.CONTENT, TaskType.POLISH],
    ),
    ModelSpec(
        id="groq/deepseek-r1-distill-70b",
        provider=Provider.GROQ,
        api_model_name="deepseek-r1-distill-llama-70b",
        display_name="DeepSeek R1 Distill 70B (Groq)",
        context_window=32768,
        quality_score=92,
        speed_score=80,
        reasoning_score=95,
        medical_score=88,
        best_for=[TaskType.VALIDATE],
    ),
    ModelSpec(
        id="gemini/gemini-2.5-flash",
        provider=Provider.GEMINI,
        api_model_name="gemini-2.5-flash-preview-05-20",
        display_name="Gemini 2.5 Flash",
        context_window=1048576,
        quality_score=90,
        speed_score=92,
        medical_score=85,
        code_score=88,
        best_for=[TaskType.EXTRACT, TaskType.VALIDATE],
    ),
    ModelSpec(
        id="gemini/gemini-2.5-pro",
        provider=Provider.GEMINI,
        api_model_name="gemini-2.5-pro-preview-05-06",
        display_name="Gemini 2.5 Pro",
        context_window=1048576,
        quality_score=95,
        speed_score=60,
        medical_score=92,
        code_score=92,
        best_for=[TaskType.CONTENT, TaskType.POLISH],
    ),
    ModelSpec(
        id="deepseek/deepseek-chat-v3",
        provider=Provider.DEEPSEEK,
        api_model_name="deepseek-chat",
        display_name="DeepSeek V3",
        context_window=65536,
        quality_score=93,
        speed_score=70,
        reasoning_score=94,
        medical_score=89,
        cost_per_1k_input=0.00014,
        cost_per_1k_output=0.00028,
        best_for=[TaskType.CONTENT, TaskType.VALIDATE],
    ),
    ModelSpec(
        id="deepseek/deepseek-reasoner",
        provider=Provider.DEEPSEEK,
        api_model_name="deepseek-reasoner",
        display_name="DeepSeek R1",
        context_window=65536,
        quality_score=95,
        speed_score=45,
        reasoning_score=98,
        medical_score=91,
        cost_per_1k_input=0.00055,
        cost_per_1k_output=0.00219,
        best_for=[TaskType.VALIDATE],
    ),
    ModelSpec(
        id="cerebras/llama-4-scout-17b",
        provider=Provider.CEREBRAS,
        api_model_name="llama-4-scout-17b-16e-instruct",
        display_name="Llama 4 Scout (Cerebras)",
        context_window=131072,
        quality_score=89,
        speed_score=98,
        medical_score=83,
        code_score=82,
        best_for=[TaskType.EXTRACT],
    ),
    # === TIER PAGO (Premium) ===
    ModelSpec(
        id="anthropic/claude-sonnet-4-5",
        provider=Provider.ANTHROPIC,
        api_model_name="claude-sonnet-4-5-20250929",
        display_name="Claude Sonnet 4.5",
        context_window=200000,
        is_free=False,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        quality_score=97,
        speed_score=75,
        medical_score=96,
        code_score=95,
        best_for=[TaskType.CONTENT, TaskType.VALIDATE, TaskType.POLISH],
    ),
    ModelSpec(
        id="anthropic/claude-opus-4-5",
        provider=Provider.ANTHROPIC,
        api_model_name="claude-opus-4-5-20250929",
        display_name="Claude Opus 4.5",
        context_window=200000,
        is_free=False,
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
        quality_score=99,
        speed_score=40,
        medical_score=98,
        code_score=97,
        best_for=[TaskType.CONTENT, TaskType.VALIDATE],
    ),
]


class ModelRegistry:
    """In-memory registry with ranking + feedback loop.

    This is designed to be integrated incrementally without breaking the existing
    LLM code paths.
    """

    def __init__(self, *, include_defaults: bool = True):
        self.models: dict[str, ModelSpec] = {}
        if include_defaults:
            for m in DEFAULT_MODELS_FEB_2026:
                self.models[m.id] = m

    def record_result(self, model_id: str, quality: float, success: bool, *, latency_ms: float | None = None) -> None:
        if model_id not in self.models:
            return
        m = self.models[model_id]
        m.total_calls += 1
        if not success:
            m.total_failures += 1
        else:
            m.real_quality_scores.append(float(quality))
            if len(m.real_quality_scores) > 100:
                m.real_quality_scores = m.real_quality_scores[-100:]
        if latency_ms is not None:
            if m.avg_latency_ms is None:
                m.avg_latency_ms = float(latency_ms)
            else:
                # EMA-ish
                m.avg_latency_ms = 0.8 * m.avg_latency_ms + 0.2 * float(latency_ms)

    def get_best_for_task(
        self,
        task: TaskType,
        *,
        free_only: bool = True,
        min_quality: int = 85,
        prefer_speed: bool = False,
    ) -> list[ModelSpec]:
        candidates = [
            m
            for m in self.models.values()
            if m.is_available and ((m.is_free) if free_only else True) and (m.quality_score >= min_quality)
        ]

        def score(m: ModelSpec) -> float:
            quality = (
                (sum(m.real_quality_scores[-20:]) / len(m.real_quality_scores[-20:]))
                if len(m.real_quality_scores) >= 5
                else float(m.quality_score)
            )
            task_bonus = 10.0 if task in (m.best_for or []) else 0.0
            medical_bonus = float(m.medical_score) * (0.15 if task in (TaskType.CONTENT, TaskType.VALIDATE) else 0.0)
            speed_weight = 0.3 if prefer_speed else 0.1
            failure_penalty = (m.total_failures / max(m.total_calls, 1)) * 20.0
            return (
                quality * 0.5
                + task_bonus
                + medical_bonus
                + float(m.speed_score) * speed_weight
                + float(m.reasoning_score) * 0.1
                - failure_penalty
            )

        candidates.sort(key=score, reverse=True)
        return candidates
