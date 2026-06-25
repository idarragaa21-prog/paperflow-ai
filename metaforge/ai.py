"""Shared AI helper — connect your own Claude or ChatGPT account.

Three ways to power the AI features, in priority order:
  1. An Anthropic (Claude) API key you paste in the app.
  2. An OpenAI (ChatGPT) API key you paste in the app.
  3. The local `claude` CLI session (run `claude login`), if no key is set.

The key is stored only on your machine (``~/.metaforge/ai_config.json``, chmod
600) and is sent only to the respective provider. Every call degrades
gracefully: callers catch failures and fall back to local deterministic
scaffolds, so the product always works offline too.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_TIMEOUT = int(os.environ.get("METAFORGE_AI_TIMEOUT", "90"))

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_ANTHROPIC_DEFAULT = "claude-3-5-sonnet-latest"
_ANTHROPIC_FAST = "claude-3-5-haiku-latest"
_OPENAI_DEFAULT = "gpt-4o"
_OPENAI_FAST = "gpt-4o-mini"


# --- config (stored locally) -------------------------------------------------
def _config_path() -> Path:
    base = os.environ.get("METAFORGE_DATA")
    root = Path(base) if base else Path.home() / ".metaforge"
    root.mkdir(parents=True, exist_ok=True)
    return root / "ai_config.json"


def load_ai_config() -> dict:
    # env overrides let power users / CI set a key without the UI
    env_anthropic = os.environ.get("ANTHROPIC_API_KEY")
    env_openai = os.environ.get("OPENAI_API_KEY")
    try:
        cfg = json.loads(_config_path().read_text())
    except Exception:  # noqa: BLE001
        cfg = {}
    if not cfg.get("api_key"):
        if env_anthropic:
            cfg = {"provider": "anthropic", "api_key": env_anthropic, "model": cfg.get("model", "")}
        elif env_openai:
            cfg = {"provider": "openai", "api_key": env_openai, "model": cfg.get("model", "")}
    return cfg


def save_ai_config(provider: str, api_key: str = "", model: str = "") -> dict:
    provider = (provider or "").strip()
    cfg = {"provider": provider, "api_key": (api_key or "").strip(), "model": (model or "").strip()}
    if provider in ("", "claude_cli"):  # CLI mode keeps no secret
        cfg["api_key"] = ""
    p = _config_path()
    p.write_text(json.dumps(cfg))
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass
    return ai_status_dict()


def _mask(key: str) -> str:
    return f"…{key[-4:]}" if key and len(key) > 4 else ("•••" if key else "")


# --- availability / status ---------------------------------------------------
def claude_bin() -> str | None:
    return shutil.which(os.environ.get("METAFORGE_CLAUDE_BIN", "claude"))


def ai_available() -> bool:
    if os.environ.get("METAFORGE_AI", "auto").lower() == "off":
        return False
    cfg = load_ai_config()
    if cfg.get("provider") in ("anthropic", "openai") and cfg.get("api_key"):
        return True
    return claude_bin() is not None


def ai_status_dict() -> dict:
    cfg = load_ai_config()
    provider = cfg.get("provider") or ("claude_cli" if claude_bin() else "")
    return {
        "ai_available": ai_available(),
        "provider": provider,
        "has_key": bool(cfg.get("api_key")),
        "masked_key": _mask(cfg.get("api_key", "")),
        "model": cfg.get("model") or "",
        "cli_available": claude_bin() is not None,
    }


# --- provider calls ----------------------------------------------------------
def _http_post_json(url: str, headers: dict, body: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")[:300]
        raise RuntimeError(f"API {exc.code}: {detail}") from exc


def _anthropic_model(cfg: dict, model: str | None) -> str:
    if model and model.lower() in ("haiku", "fast"):
        return _ANTHROPIC_FAST
    if model and model.startswith("claude-3") or (model and model.count("-") >= 2 and "claude" in model):
        return model
    return cfg.get("model") or _ANTHROPIC_DEFAULT


def _openai_model(cfg: dict, model: str | None) -> str:
    if model and model.lower() in ("haiku", "fast"):
        return _OPENAI_FAST
    if model and model.startswith("gpt"):
        return model
    return cfg.get("model") or _OPENAI_DEFAULT


def _call_anthropic(prompt: str, key: str, model: str, timeout: int) -> str:
    data = _http_post_json(_ANTHROPIC_URL,
                           {"x-api-key": key, "anthropic-version": "2023-06-01"},
                           {"model": model, "max_tokens": 8192,
                            "messages": [{"role": "user", "content": prompt}]}, timeout)
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def _call_openai(prompt: str, key: str, model: str, timeout: int) -> str:
    data = _http_post_json(_OPENAI_URL, {"Authorization": f"Bearer {key}"},
                           {"model": model, "messages": [{"role": "user", "content": prompt}]}, timeout)
    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")


# --- unified entry point (name kept for back-compat) -------------------------
def run_claude(prompt: str, *, timeout: int = DEFAULT_TIMEOUT, model: str | None = None,
               cwd: str | None = None) -> str:
    """Run one AI turn via the configured provider; return its text result.

    Routes to the Anthropic or OpenAI API when a key is configured, otherwise to
    the local `claude` CLI. `model` may be a CLI/alias hint ("haiku" = fast).
    `cwd` only applies to the CLI (so it can read local files like figure images).
    """
    cfg = load_ai_config()
    provider = cfg.get("provider") or ""
    key = cfg.get("api_key") or ""
    if provider == "anthropic" and key:
        return _call_anthropic(prompt, key, _anthropic_model(cfg, model), timeout)
    if provider == "openai" and key:
        return _call_openai(prompt, key, _openai_model(cfg, model), timeout)

    binary = claude_bin()
    if not binary:
        raise RuntimeError("No hay IA conectada: pega una clave de API o ejecuta `claude login`.")
    cmd = [binary, "-p", prompt, "--output-format", "json"]
    cli_model = model or os.environ.get("METAFORGE_CLAUDE_MODEL")
    if cli_model:
        cmd += ["--model", cli_model]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          stdin=subprocess.DEVNULL, cwd=cwd)
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {(proc.stderr or '')[:200]}")
    envelope = json.loads(proc.stdout)
    if envelope.get("is_error"):
        raise RuntimeError("claude CLI returned an error")
    return envelope.get("result", "")


def test_connection(timeout: int = 30) -> dict:
    """Send a tiny prompt through the configured provider to verify it works."""
    try:
        txt = run_claude('Responde solo con: {"ok": true}', timeout=timeout, model="haiku")
        return {"ok": True, "sample": (txt or "")[:60]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:200]}


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


def run_claude_json(prompt: str, *, timeout: int = DEFAULT_TIMEOUT, model: str | None = None,
                    cwd: str | None = None) -> dict:
    return extract_json(run_claude(prompt, timeout=timeout, model=model, cwd=cwd))
