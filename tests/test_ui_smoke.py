"""Headless-browser smoke test: load the app, walk all 8 steps and exercise the
interactive controls, asserting ZERO console/page errors — the "funciona todo
sin errores" guarantee for the UI itself.

Skips cleanly when Playwright or a Chromium binary isn't available (e.g. CI),
so it never blocks the rest of the suite.
"""
from __future__ import annotations

import glob
import os
import threading
import time

import pytest

pytest.importorskip("playwright.sync_api")
pytest.importorskip("uvicorn")


def _chrome() -> str | None:
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux64/chrome",
                os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def test_ui_walks_every_step_without_errors():
    chrome = _chrome()
    if not chrome:
        pytest.skip("no Chromium binary available for rendering")

    import uvicorn
    from playwright.sync_api import sync_playwright
    from metaforge.api import app

    port = 8019
    cfg = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(cfg)
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)

    errors: list[str] = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=chrome)
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(f"http://127.0.0.1:{port}/", wait_until="networkidle")
            pg.click("#demoBtn")
            pg.wait_for_timeout(1500)
            for s in range(1, 9):
                pg.click(f"#navstep-{s}")
                pg.wait_for_timeout(250)
            pg.click("#navstep-8")
            pg.wait_for_timeout(200)
            pg.click("#previewToggle")
            pg.wait_for_timeout(200)
            b.close()
    finally:
        server.should_exit = True

    assert not errors, f"UI produced console/page errors: {errors}"
