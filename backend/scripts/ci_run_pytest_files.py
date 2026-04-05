#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = BACKEND_DIR / "tests"
TIMEOUT_SECONDS = int(os.getenv("PYTEST_FILE_TIMEOUT_SECONDS", "300"))


def _collect_test_files() -> list[Path]:
    files = sorted(TESTS_DIR.glob("test_*.py"))
    if not files:
        raise RuntimeError(f"No test files found under {TESTS_DIR}")
    return files


def _run_one(test_file: Path) -> int:
    rel = test_file.relative_to(BACKEND_DIR)
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--tb=short",
        "--maxfail=1",
        str(rel),
    ]

    print(f"[ci_pytest] running {rel} (timeout={TIMEOUT_SECONDS}s)", flush=True)
    started = time.monotonic()
    try:
        subprocess.run(cmd, cwd=BACKEND_DIR, check=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - started
        print(f"[ci_pytest] TIMEOUT: {rel} exceeded {TIMEOUT_SECONDS}s (elapsed={elapsed:.1f}s)", flush=True)
        return 124
    except subprocess.CalledProcessError as exc:
        elapsed = time.monotonic() - started
        print(f"[ci_pytest] FAIL: {rel} exited with {exc.returncode} (elapsed={elapsed:.1f}s)", flush=True)
        return exc.returncode

    elapsed = time.monotonic() - started
    print(f"[ci_pytest] ok: {rel} ({elapsed:.1f}s)", flush=True)
    return 0


def main() -> int:
    files = _collect_test_files()
    print(f"[ci_pytest] collected {len(files)} files", flush=True)

    for file in files:
        code = _run_one(file)
        if code != 0:
            return code

    print("[ci_pytest] all test files passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
