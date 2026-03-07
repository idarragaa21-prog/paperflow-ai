from __future__ import annotations

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except Exception:  # pragma: no cover
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _NoopMetric:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

    def Counter(*args, **kwargs):  # type: ignore[misc]
        return _NoopMetric()

    def Histogram(*args, **kwargs):  # type: ignore[misc]
        return _NoopMetric()

    def generate_latest():  # type: ignore[misc]
        return b""


auth_login_attempts_total = Counter("auth_login_attempts_total", "Login attempts", ["result"])
auth_rate_limited_total = Counter("auth_rate_limited_total", "Auth requests rate limited", ["endpoint"])
token_refresh_reuse_total = Counter("token_refresh_reuse_total", "Refresh reuse detections")
chat_grounded_answers_total = Counter("chat_grounded_answers_total", "Grounded chat answers")
chat_blocked_answers_total = Counter("chat_blocked_answers_total", "Blocked chat answers")
library_query_duration_seconds = Histogram("library_query_duration_seconds", "Project library query latency")
job_retries_total = Counter("job_retries_total", "Job retries", ["queue"])
job_failures_total = Counter("job_failures_total", "Job failures", ["queue"])
permission_denials_total = Counter("permission_denials_total", "Permission denials", ["resource", "required_role"])
