"""
Locust load test for the clinical pipeline endpoints.

Usage (requires a running PaperFlow AI server):

    pip install locust
    locust -f scripts/load_test_clinical.py --headless \
           -u 20 -r 5 -t 60s \
           --host=http://localhost:8000

    # With web UI (open http://localhost:8089):
    locust -f scripts/load_test_clinical.py --host=http://localhost:8000

Environment variables:
    LT_EMAIL      - Test user email    (default: stress@example.com)
    LT_PASSWORD   - Test user password (default: testpassword)
    LT_TOPIC      - Clinical topic to query (default: see TOPICS list below)

Metrics to observe:
    - Response time p50 / p95 / p99
    - Failure rate (should be 0% for non-rate-limited requests)
    - Requests/second sustained throughput
    - 429 rate (expected ≥ 3 req/user/min beyond the limit)
"""
from __future__ import annotations

import os
import random

from locust import HttpUser, between, events, task

# ── Configuration ─────────────────────────────────────────────────────────────

LT_EMAIL = os.getenv("LT_EMAIL", "stress@example.com")
LT_PASSWORD = os.getenv("LT_PASSWORD", "testpassword")

TOPICS = [
    "Hypertension management in elderly patients",
    "SGLT2 inhibitors in heart failure with preserved ejection fraction",
    "ACL reconstruction outcomes in athletes over 40",
    "Beta-blocker use in chronic obstructive pulmonary disease",
    "Antibiotic prophylaxis in orthopedic surgery",
    "Metformin vs GLP-1 agonists as first-line therapy in T2DM",
    "Indications for thrombolysis in acute ischemic stroke",
    "Corticosteroid tapering protocols in rheumatoid arthritis",
]


# ── User behavior ─────────────────────────────────────────────────────────────


class ClinicalPipelineUser(HttpUser):
    """Simulates a researcher generating clinical sheets."""

    wait_time = between(2, 8)  # seconds between tasks (realistic think time)

    def on_start(self) -> None:
        """Login and obtain CSRF token before running tasks."""
        self._access_token: str | None = None
        self._csrf_token: str | None = None
        self._login()

    def _login(self) -> None:
        resp = self.client.post(
            "/auth/login",
            json={"email": LT_EMAIL, "password": LT_PASSWORD},
            name="/auth/login",
        )
        if resp.status_code == 200:
            # Extract CSRF token from cookie
            self._csrf_token = resp.cookies.get("csrf_token")
        else:
            print(f"[load_test] Login failed: {resp.status_code} — {resp.text[:200]}")

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self._csrf_token:
            h["X-CSRF-Token"] = self._csrf_token
        return h

    @task(3)
    def query_clinical_sheet(self) -> None:
        """POST /clinical/query — primary load scenario."""
        topic = random.choice(TOPICS)
        resp = self.client.post(
            "/clinical/query",
            json={
                "topic": topic,
                "level": "general",
                "focus": "general",
                "max_length": "medium",
            },
            headers=self._headers(),
            name="/clinical/query",
        )
        if resp.status_code == 429:
            # Rate limiting is expected — mark as success to track separately
            resp.success()  # type: ignore[attr-defined]
        elif resp.status_code >= 500:
            resp.failure(f"Server error: {resp.status_code}")  # type: ignore[attr-defined]

    @task(1)
    def list_clinical_sheets(self) -> None:
        """GET /clinical/sheets — lightweight read operation."""
        self.client.get(
            "/clinical/sheets",
            headers=self._headers(),
            name="/clinical/sheets [list]",
        )

    @task(1)
    def check_job_status(self) -> None:
        """GET /jobs — check background job queue status."""
        self.client.get(
            "/jobs",
            headers=self._headers(),
            name="/jobs [list]",
        )


# ── Custom stats event ────────────────────────────────────────────────────────


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **_kwargs):
    """Log rate-limit hits separately for analysis."""
    if hasattr(response, "status_code") and response.status_code == 429:
        print(f"[load_test] Rate limited on {name} — retry-after: {response.headers.get('Retry-After', '?')}s")
