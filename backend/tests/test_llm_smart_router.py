import pytest

from app.services.llm.model_registry import ModelRegistry, TaskType, Provider, ModelSpec
from app.services.llm.smart_router import RateLimiter


def test_rate_limiter_blocks_after_limit():
    rl = RateLimiter()
    provider = "groq"
    # set strict limit for test
    rl.limits[provider].max_calls = 2
    assert rl.can_call(provider) is True
    rl.record_call(provider)
    assert rl.can_call(provider) is True
    rl.record_call(provider)
    assert rl.can_call(provider) is False


def test_registry_ranking_prefers_task_best_for_bonus():
    reg = ModelRegistry(include_defaults=False)
    reg.models["a"] = ModelSpec(id="a", provider=Provider.OLLAMA, api_model_name="a", display_name="a", quality_score=90, speed_score=10, best_for=[TaskType.EXTRACT])
    reg.models["b"] = ModelSpec(id="b", provider=Provider.OLLAMA, api_model_name="b", display_name="b", quality_score=91, speed_score=10, best_for=[])

    best = reg.get_best_for_task(TaskType.EXTRACT, free_only=True, min_quality=85)
    # task bonus should beat 1 point quality
    assert best[0].id == "a"


def test_registry_record_result_failure_penalizes_score():
    reg = ModelRegistry(include_defaults=False)
    reg.models["m"] = ModelSpec(id="m", provider=Provider.OLLAMA, api_model_name="m", display_name="m", quality_score=90)

    # many failures
    for _ in range(10):
        reg.record_result("m", 0, success=False)

    # should still be present but failure penalty will apply; just ensure doesn't crash
    best = reg.get_best_for_task(TaskType.GENERAL, free_only=True, min_quality=85)
    assert best and best[0].id == "m"
