from app.services.llm.model_registry import ModelSpec, Provider
from app.services.llm.provider_adapters import get_adapter, OpenClawChatAdapter


def test_get_adapter_routes_vendor_models_through_openclaw():
    m = ModelSpec(
        id="groq/llama-4-scout-17b",
        provider=Provider.GROQ,
        api_model_name="meta-llama/llama-4-scout-17b-16e-instruct",
        display_name="x",
    )
    a = get_adapter(m)
    assert isinstance(a, OpenClawChatAdapter)
