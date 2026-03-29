from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    PROJECT_DEFAULT_RUNTIME_MODE: str = "local_only"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    PAPERFLOW_CHAT_MODEL: str = "qwen2.5:7b"
    PAPERFLOW_EXTRACTION_MODEL: str = "qwen2.5:7b"
    PAPERFLOW_WRITING_MODEL: str = "llama3.1:8b"
    PAPERFLOW_EMBEDDING_MODEL: str = "bge-m3"
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
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20240620"
    CLAUDE_MAX_TOKENS: int = 4096
    CLAUDE_TEMPERATURE: float = 0.3

    # CORS
    # Vite dev server typically runs on localhost:5173 or 127.0.0.1:5173
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True

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
        return None if self.ENV == "development" else "yourdomain.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
