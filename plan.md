1. **Analyze test failures**:
   - `tests/test_runtime_health.py` fails on `test_collect_runtime_health_marks_missing_ollama_models_as_degraded` because `llm_runtime` status is `ok` instead of `degraded`. Memory states: "When testing runtime health checks for the LLM service (`backend/tests/test_runtime_health.py`), explicitly monkeypatch `settings.LLM_PROVIDER` (e.g., to 'auto_local') to ensure the correct provider mode logic is evaluated, avoiding false positives where the test asserts a 'degraded' status but receives 'ok'." I need to add `monkeypatch.setattr(runtime_health.settings, "LLM_PROVIDER", "auto_local")` to this test.
   - `frontend/src/test/SettingsPage.test.tsx` fails because it expects "Passwords do not match." text but cannot find it. Memory states: "The frontend test suite has a known, pre-existing assertion failure in `src/test/SettingsPage.test.tsx` ('blocks password change when confirmation does not match'). Do not attempt to fix it if it is unrelated to the current task's scope." I can ignore this frontend test failure.

2. **Fix `test_runtime_health.py`**:
   - Call `replace_with_git_merge_diff` to add `monkeypatch.setattr(runtime_health.settings, "LLM_PROVIDER", "auto_local")` to `test_collect_runtime_health_marks_missing_ollama_models_as_degraded`.

3. **Verify tests**:
   - Run `cd backend && PYTHONPATH=. pytest tests/test_runtime_health.py`.

4. **Format/Lint**:
   - Run `ruff format` and `ruff check` on the modified file.

5. **Submit**: Submit the PR again.
