import re

with open("backend/app/services/runtime_health.py", "r") as f:
    content = f.read()

# Ah! The status of ollama_payload was already assigned!
# But let's check `ollama_status` and `openclaw_payload["status"]`.
# The test mocks:
# {"models": [{"name": runtime_health.settings.PAPERFLOW_CHAT_MODEL}]}
# Which means "embedding" (which uses PAPERFLOW_EMBEDDING_MODEL) is NOT in the mock!
# Therefore, `missing_required_models` should contain `settings.PAPERFLOW_EMBEDDING_MODEL`.
# If `missing_required_models` is populated, `ollama_status` is set to "degraded".
# BUT if `ollama_payload["status"]` is "degraded", why was it returning "ok"?
