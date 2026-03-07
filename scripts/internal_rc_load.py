#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from typing import Any

import httpx


async def _login(client: httpx.AsyncClient, *, email: str, password: str) -> None:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    response.raise_for_status()


async def _find_project(client: httpx.AsyncClient, *, title: str) -> dict[str, Any]:
    response = await client.get("/projects")
    response.raise_for_status()
    for project in response.json():
        if project["title"] == title:
            return project
    raise RuntimeError(f"Project not found: {title}")


async def _measure(coro) -> tuple[float, Any]:
    started = time.perf_counter()
    result = await coro
    return time.perf_counter() - started, result


async def _library_page(client: httpx.AsyncClient, project_id: str) -> dict[str, Any]:
    response = await client.get(f"/projects/{project_id}/library", params={"limit": 50})
    response.raise_for_status()
    return response.json()


async def _chat_once(client: httpx.AsyncClient, project_id: str) -> dict[str, Any]:
    response = await client.post(
        f"/projects/{project_id}/chat",
        json={"question": "What main effect is reported by the seeded remote monitoring studies?", "task_type": "chat", "max_citations": 3},
    )
    response.raise_for_status()
    return response.json()


async def _enqueue_process(client: httpx.AsyncClient, paper_id: str) -> dict[str, Any]:
    response = await client.post(f"/papers/{paper_id}/process")
    response.raise_for_status()
    return response.json()


async def _run(args) -> int:
    async with httpx.AsyncClient(base_url=args.base_url, timeout=120.0, follow_redirects=True) as client:
        await _login(client, email=args.email, password=args.password)
        project = await _find_project(client, title=args.project_title)
        project_id = project["id"]

        library_timings = await asyncio.gather(*[_measure(_library_page(client, project_id)) for _ in range(args.library_requests)])
        library_page = library_timings[0][1]
        first_paper_id = (library_page.get("items") or [{}])[0].get("id")
        if not first_paper_id:
            raise RuntimeError("No seeded papers found for load test")

        chat_timings = await asyncio.gather(*[_measure(_chat_once(client, project_id)) for _ in range(args.chat_requests)])
        process_results = await asyncio.gather(*[_enqueue_process(client, first_paper_id) for _ in range(args.job_requests)])

        library_latencies = [seconds for seconds, _ in library_timings]
        chat_latencies = [seconds for seconds, _ in chat_timings]
        chat_payloads = [payload for _, payload in chat_timings]

        report = {
            "library": {
                "requests": args.library_requests,
                "mean_seconds": round(statistics.mean(library_latencies), 3),
                "p95_seconds": round(sorted(library_latencies)[max(0, int(len(library_latencies) * 0.95) - 1)], 3),
                "items_first_page": len(library_page.get("items") or []),
            },
            "chat": {
                "requests": args.chat_requests,
                "mean_seconds": round(statistics.mean(chat_latencies), 3),
                "grounded_responses": sum(1 for payload in chat_payloads if payload.get("grounded")),
                "blocked_responses": sum(1 for payload in chat_payloads if payload.get("blocked_reason")),
            },
            "jobs": {
                "requests": args.job_requests,
                "job_ids": [payload.get("job_id") for payload in process_results],
            },
        }
        print(report)
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a lightweight internal RC load smoke against the running API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--email", default="rc-owner@paperflow.local")
    parser.add_argument("--password", default="paperflow-e2e-123")
    parser.add_argument("--project-title", default="Internal RC Fixture")
    parser.add_argument("--library-requests", type=int, default=12)
    parser.add_argument("--chat-requests", type=int, default=4)
    parser.add_argument("--job-requests", type=int, default=3)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
