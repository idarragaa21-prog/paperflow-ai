from __future__ import annotations

from pathlib import Path

import pytest

from app.config import BACKEND_ENV_FILE, Settings, resolve_settings_env_file


def test_settings_parse_comma_separated_cors_origins():
    settings = Settings(
        SECRET_KEY="test",
        BACKEND_CORS_ORIGINS="https://paperflow-web.vercel.app, https://paperflow-api.onrender.com/",
        PAPERFLOW_DISABLE_DOTENV="1",
    )

    assert settings.BACKEND_CORS_ORIGINS == [
        "https://paperflow-web.vercel.app",
        "https://paperflow-api.onrender.com",
    ]


def test_settings_parse_cors_origins_invalid_json():
    with pytest.raises(ValueError, match="BACKEND_CORS_ORIGINS must be a JSON array or comma-separated list"):
        Settings(
            BACKEND_CORS_ORIGINS='[ "https://paperflow.ai"',
            PAPERFLOW_DISABLE_DOTENV="1",
        )


def test_settings_parse_cors_origins_valid_json_array():
    settings = Settings(
        BACKEND_CORS_ORIGINS='["https://paperflow-web.vercel.app", "https://paperflow-api.onrender.com"]',
        PAPERFLOW_DISABLE_DOTENV="1",
    )

    assert settings.BACKEND_CORS_ORIGINS == [
        "https://paperflow-web.vercel.app",
        "https://paperflow-api.onrender.com",
    ]


def test_production_settings_require_non_local_frontend_origin():
    with pytest.raises(ValueError, match="real frontend origin"):
        Settings(
            ENV="production",
            SECRET_KEY="super-secret",
            STORAGE_BACKEND="filesystem",
            BACKEND_CORS_ORIGINS="http://localhost:5173",
            PAPERFLOW_DISABLE_DOTENV="1",
        )


def test_resolve_settings_env_file_uses_backend_env_by_default(monkeypatch):
    monkeypatch.delenv("PAPERFLOW_DISABLE_DOTENV", raising=False)

    assert resolve_settings_env_file() == str(Path(BACKEND_ENV_FILE))


def test_resolve_settings_env_file_can_disable_dotenv(monkeypatch):
    monkeypatch.setenv("PAPERFLOW_DISABLE_DOTENV", "1")

    assert resolve_settings_env_file() is None


def test_mail_enabled_requires_smtp_host_and_sender_in_production():
    with pytest.raises(ValueError, match="MAIL_ENABLED requires"):
        Settings(
            ENV="production",
            SECRET_KEY="super-secret",
            STORAGE_BACKEND="filesystem",
            BACKEND_CORS_ORIGINS="https://paperflow.ai",
            APP_BASE_URL="https://paperflow.ai",
            MAIL_ENABLED=True,
            PAPERFLOW_DISABLE_DOTENV="1",
        )
