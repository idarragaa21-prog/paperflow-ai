import re
with open("backend/tests/test_runtime_health.py", "r") as f:
    content = f.read()

content = content.replace(
    'monkeypatch.setattr(runtime_health.settings, "PAPERFLOW_EMBEDDING_MODEL", "bge-m3")',
    'monkeypatch.setattr(runtime_health.settings, "PAPERFLOW_EMBEDDING_MODEL", "bge-m3")\n    monkeypatch.setattr(runtime_health.settings, "LLM_PROVIDER", "auto_local")'
)

with open("backend/tests/test_runtime_health.py", "w") as f:
    f.write(content)
