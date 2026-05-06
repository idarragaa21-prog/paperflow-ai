import re

with open("backend/tests/test_runtime_health.py", "r") as f:
    content = f.read()

# According to memory: "When testing runtime health checks for the LLM service
# (`backend/tests/test_runtime_health.py`), explicitly monkeypatch `settings.LLM_PROVIDER`
# (e.g., to 'auto_local') to ensure the correct provider mode logic is evaluated,
# avoiding false positives where the test asserts a 'degraded' status but receives 'ok'."

new_content = content.replace(
    'monkeypatch.setattr(runtime_health.settings, "PAPERFLOW_EMBEDDING_MODEL", "bge-m3")',
    'monkeypatch.setattr(runtime_health.settings, "PAPERFLOW_EMBEDDING_MODEL", "bge-m3")\n    monkeypatch.setattr(runtime_health.settings, "LLM_PROVIDER", "auto_local")'
)

with open("backend/tests/test_runtime_health.py", "w") as f:
    f.write(new_content)
