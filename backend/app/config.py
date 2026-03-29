from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlparse

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
BACKEND_ENV_FILE = BACKEND_DIR / ".env"


def resolve_settings_env_file() -> str | None:
    disabled = str(os.getenv("PAPERFLOW_DISABLE_DOTENV", "")).strip().lower()
    if disabled in {"1", "true", "yes", "on"}:
        return None
    return str(BACKEND_ENV_FILE)


class Settings(BaseSettings):
    # Environment
    ENV: str = "development"  # development | production

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/paperflow_ai"

    # Security
    # WARNING: Override this via the SECRET_KEY environment variable before deploying.
    # A weak default is kept here only to allow local dev without any .env file.
    # In production (ENV=production) startup will abort if this default is detected.
    SECRET_KEY: str = "CHANGE_ME"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis (rate limiting + jobs)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    STORAGE_BASE_PATH: str = "~/PaperFlowAIData"
    STORAGE_BACKEND: str = "filesystem"  # filesystem | s3
    S3_ENDPOINT_URL: str | None = "http://127.0.0.1:9000"
    S3_ACCESS_KEY: str = "paperflow"
    S3_SECRET_KEY: str = "paperflow123"
    S3_BUCKET: str = "paperflow-artifacts"
    S3_REGION: str = "us-east-1"
    S3_FORCE_PATH_STYLE: bool = True
    S3_AUTO_CREATE_BUCKET: bool = True

    # Open access / resolvers
    UNPAYWALL_EMAIL: str = "idarragaa21@gmail.com"

    # Meta-analysis extractor
    META_MAX_CONCURRENT: int = 3
    OCR_ENABLED: bool = False

    # LLM
    LLM_PROVIDER: str = "openclaw"  # openclaw | direct_claude
    LLM_STRATEGY: str = "single"  # single | ensemble
    CLINICAL_LLM_PROVIDER: str = "claude"  # claude | openai
    PROJECT_DEFAULT_RUNTIME_MODE: str = "local_only"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    PAPERFLOW_CHAT_MODEL: str = "qwen2.5-coder:7b"
    PAPERFLOW_EXTRACTION_MODEL: str = "qwen2.5-coder:7b"
    PAPERFLOW_WRITING_MODEL: str = "qwen2.5-coder:7b"
    PAPERFLOW_EMBEDDING_MODEL: str = "nomic-embed-text:latest"
    QDRANT_URL: str = "http://127.0.0.1:6333"
    QDRANT_COLLECTION_PREFIX: str = "paperflow"
    R_ENGINE_URL: str = "http://127.0.0.1:8010"
    GROBID_URL: str = "http://127.0.0.1:8070"
    GROBID_ENABLED: bool = True
    GROBID_TIMEOUT_SECONDS: int = 45

    CHAT_MIN_RETRIEVED_CHUNKS: int = 2
    CHAT_MIN_GROUNDED_SCORE: float = 0.35
    CHAT_ENABLE_INTERNAL_DEBUG: bool = False
    CHAT_DEFAULT_MODE: str = "extractive_strict"

    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "paperflow-backend"

    PRESENTATION_SLIDE_TARGET: int = 36
    PRESENTATION_SLIDE_MIN: int = 30
    PRESENTATION_SLIDE_MAX: int = 40

    # OpenClaw (multi-vendor routing)
    OPENCLAW_BASE_URL: str = "http://127.0.0.1:18789"  # OpenClaw server
    OPENCLAW_TIMEOUT: int = 120
    OPENCLAW_GATEWAY_TOKEN: str | None = None

    # Multi-pass model refs used by Clinical PRO pipeline.
    # Defaults are intentionally "default" so a single configured provider (e.g. Groq) works out of the box.
    # Override via env if you have multiple providers configured in OpenClaw.
    OPENCLAW_CLAUDE_MODEL: str = "default"
    OPENCLAW_OPENAI_MODEL: str = "default"
    OPENCLAW_GEMINI_MODEL: str = "default"

    # Default/single-model fallback (if LLM_STRATEGY=single)
    OPENCLAW_MODEL: str = "default"

    # Optional direct providers (limited)
    ANTHROPIC_API_KEY: str | None = None
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_MAX_TOKENS: int = 4096
    CLAUDE_TEMPERATURE: float = 0.3

    # App URLs / email delivery
    APP_BASE_URL: str = "http://127.0.0.1:5173"
    MAIL_ENABLED: bool = False
    MAIL_FROM_EMAIL: str | None = None
    MAIL_SMTP_HOST: str | None = None
    MAIL_SMTP_PORT: int = 587
    MAIL_SMTP_USERNAME: str | None = None
    MAIL_SMTP_PASSWORD: str | None = None
    MAIL_SMTP_USE_TLS: bool = True
    MAIL_SMTP_USE_SSL: bool = False

    # CORS
    # Default: localhost dev servers. Override via env for production.
    # Example: BACKEND_CORS_ORIGINS=["https://app.paperflow.ai","https://paperflow.ai"]
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    COOKIE_SAMESITE: str | None = None

    # Cookie domain — set via env for production.
    # None = browser default (current domain only). Set to ".yourdomain.com" for subdomains.
    COOKIE_DOMAIN: str | None = None

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, list):
            return [cls._normalize_origin(item) for item in value if str(item or "").strip()]
        if value is None:
            return []

        raw = str(value).strip()
        if not raw:
            return []

        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError("BACKEND_CORS_ORIGINS must be a JSON array or comma-separated list") from exc
            if not isinstance(parsed, list):
                raise ValueError("BACKEND_CORS_ORIGINS JSON value must be an array")
            return [cls._normalize_origin(item) for item in parsed if str(item or "").strip()]

        return [cls._normalize_origin(item) for item in raw.split(",") if str(item or "").strip()]

    @field_validator("COOKIE_DOMAIN", mode="before")
    @classmethod
    def normalize_cookie_domain(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("COOKIE_SAMESITE", mode="before")
    @classmethod
    def normalize_cookie_samesite(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip().lower()
        return cleaned or None

    @field_validator("MAIL_FROM_EMAIL", "MAIL_SMTP_HOST", "MAIL_SMTP_USERNAME", "MAIL_SMTP_PASSWORD", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value):
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    @field_validator("APP_BASE_URL", mode="before")
    @classmethod
    def normalize_app_base_url(cls, value):
        raw = str(value or "").strip().rstrip("/")
        return raw or "http://127.0.0.1:5173"

    @field_validator("CLINICAL_LLM_PROVIDER", mode="before")
    @classmethod
    def normalize_clinical_llm_provider(cls, value):
        cleaned = str(value or "").strip().lower()
        return cleaned or "claude"

    @classmethod
    def _normalize_origin(cls, value) -> str:
        origin = str(value or "").strip().rstrip("/")
        if not origin:
            raise ValueError("CORS origins cannot be empty")
        if origin == "*":
            return origin
        parsed = urlparse(origin)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid CORS origin: {origin}")
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def _is_local_origin(origin: str) -> bool:
        normalized = str(origin or "").lower()
        return "localhost" in normalized or "127.0.0.1" in normalized

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        # Render provides postgres:// but asyncpg needs postgresql+asyncpg://
        if url.startswith('postgres://'):
            url = 'postgresql+asyncpg://' + url[len('postgres://'):]
        elif url.startswith('postgresql://') and '+asyncpg' not in url:
            url = 'postgresql+asyncpg://' + url[len('postgresql://'):]
        return url

    @property
    def cookie_secure(self) -> bool:
        return self.ENV == "production"

    @property
    def cookie_domain(self) -> str | None:
        return self.COOKIE_DOMAIN

    @property
    def cookie_samesite(self) -> str:
        if self.COOKIE_SAMESITE:
            return self.COOKIE_SAMESITE
        return "none" if self.ENV == "production" else "lax"

    @property
    def invitation_base_url(self) -> str:
        parsed = urlparse(self.APP_BASE_URL)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("APP_BASE_URL must be an absolute URL")
        return f"{parsed.scheme}://{parsed.netloc}"

    @property
    def mail_configured(self) -> bool:
        if not self.MAIL_ENABLED:
            return False
        if not self.MAIL_SMTP_HOST or not self.MAIL_FROM_EMAIL:
            return False
        return True

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.CLINICAL_LLM_PROVIDER not in {"claude", "openai"}:
            raise ValueError("CLINICAL_LLM_PROVIDER must be one of: claude, openai")

        if self.cookie_samesite not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be one of: lax, strict, none")
        if self.MAIL_SMTP_USE_TLS and self.MAIL_SMTP_USE_SSL:
            raise ValueError("MAIL_SMTP_USE_TLS and MAIL_SMTP_USE_SSL cannot both be enabled")
        parsed_app_base = urlparse(self.APP_BASE_URL)
        if not parsed_app_base.scheme or not parsed_app_base.netloc:
            raise ValueError("APP_BASE_URL must be an absolute URL")

        if self.ENV != "production":
            return self

        insecure_secret = self.SECRET_KEY.startswith("DEV_ONLY") or self.SECRET_KEY == "CHANGE_ME"
        insecure_access = self.S3_ACCESS_KEY.startswith("DEV_ONLY")
        insecure_secret_key = self.S3_SECRET_KEY.startswith("DEV_ONLY")
        if insecure_secret:
            raise ValueError("SECRET_KEY must be set in production")
        if self.STORAGE_BACKEND == "s3" and (insecure_access or insecure_secret_key):
            raise ValueError("S3 credentials must be set in production")
        if not self.BACKEND_CORS_ORIGINS:
            raise ValueError("BACKEND_CORS_ORIGINS must be explicitly set in production")
        if any(origin == "*" for origin in self.BACKEND_CORS_ORIGINS):
            raise ValueError("BACKEND_CORS_ORIGINS cannot use '*' when credentials are enabled")
        if all(self._is_local_origin(origin) for origin in self.BACKEND_CORS_ORIGINS):
            raise ValueError("BACKEND_CORS_ORIGINS must include the real frontend origin in production")
        if self.MAIL_ENABLED and not self.mail_configured:
            raise ValueError("MAIL_ENABLED requires MAIL_SMTP_HOST and MAIL_FROM_EMAIL")
        return self

    model_config = SettingsConfigDict(env_file=resolve_settings_env_file(), extra="ignore")


settings = Settings()
