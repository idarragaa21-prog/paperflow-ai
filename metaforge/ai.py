"""Shared AI helper: talks to the locally installed, logged-in Claude CLI.

MetaForge never asks for an API key. When it needs AI (research questions,
protocols, manuscript drafting) it shells out to the `claude` CLI you already
authenticated with `claude login`, using your existing Claude subscription.
Every call degrades gracefully: callers catch failures and fall back to local
deterministic scaffolds, so the product always works offline too.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

DEFAULT_TIMEOUT = int(os.environ.get("METAFORGE_AI_TIMEOUT", "90"))


def claude_bin() -> str | None:
    """Path to the claude CLI, or None if not installed."""
    return shutil.which(os.environ.get("METAFORGE_CLAUDE_BIN", "claude"))


def ai_available() -> bool:
    if os.environ.get("METAFORGE_AI", "auto").lower() == "off":
        return False
    return claude_bin() is not None


def run_claude(prompt: str, *, timeout: int = DEFAULT_TIMEOUT, model: str | None = None) -> str:
    """Run a single non-interactive Claude turn and return its text result.

    `model` overrides the model for this call (e.g. a faster model for bulk data
    extraction); falls back to METAFORGE_CLAUDE_MODEL, then the account default.
    """
    binary = claude_bin()
    if not binary:
        raise RuntimeError("claude CLI not found (run `claude login`)")
    cmd = [binary, "-p", prompt, "--output-format", "json"]
    model = model or os.environ.get("METAFORGE_CLAUDE_MODEL")
    if model:
        cmd += ["--model", model]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {(proc.stderr or '')[:200]}")
    envelope = json.loads(proc.stdout)
    if envelope.get("is_error"):
        raise RuntimeError("claude CLI returned an error")
    return envelope.get("result", "")


def extract_json(text: str) -> dict:
    """Pull a JSON object out of a model response (tolerates fences / prose)."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def run_claude_json(prompt: str, *, timeout: int = DEFAULT_TIMEOUT, model: str | None = None) -> dict:
    return extract_json(run_claude(prompt, timeout=timeout, model=model))
