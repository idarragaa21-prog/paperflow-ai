from __future__ import annotations

import pytest

from app.config import Settings


def test_settings_parse_comma_separated_cors_origins():
    settings = Settings(
        BACKEND_CORS_ORIGINS="https://paperflow-web.vercel.app, https://paperflow-api.onrender.com/",
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
