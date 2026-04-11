from __future__ import annotations

from app.main import app


def _is_legacy_path(path: str) -> bool:
    legacy_prefixes = (
        "/billing",
        "/books",
        "/presentations",
        "/clinical/sheets",
    )
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in legacy_prefixes)


def test_legacy_routers_removed_from_app_surface() -> None:
    legacy_paths = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if path and _is_legacy_path(path):
            legacy_paths.append(path)

    assert legacy_paths == []
