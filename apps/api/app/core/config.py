"""Application configuration using Pydantic Settings."""

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with production validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Environment & Logging
    APP_NAME: str = "CodeGuard AI"
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    DEBUG: bool = False

    # URLs
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"

    # Build & Release Versioning
    APP_VERSION: str = "1.0.0"
    GIT_REVISION: str = "v1.0.0-release"

    # Database & Redis
    DATABASE_URL: str = "postgresql://codeguard:codeguard@localhost:5432/codeguard"
    REDIS_URL: str = "redis://localhost:6379/0"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # GitHub App Credentials
    GITHUB_APP_ID: str = "dev-app-id"
    GITHUB_PRIVATE_KEY: str = ""
    GITHUB_WEBHOOK_SECRET: str = "dev-webhook-secret"
    GITHUB_CLIENT_ID: str = "dev-client-id"
    GITHUB_CLIENT_SECRET: str = "dev-client-secret"

    # Review Job & Webhook Settings
    IGNORE_DRAFT_PRS: bool = False
    CELERY_TASK_ALWAYS_EAGER: bool = False  # Set to True for synchronous testing

    # Phase 3: AI Agent & LLM Provider Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL_FAST: str = "gemini-2.5-flash"
    GEMINI_MODEL_REASONING: str = "gemini-2.5-pro"
    LLM_PROVIDER: Literal["gemini", "mock"] = "gemini"

    # Agent Execution Boundaries & Concurrency
    AGENT_MAX_CONCURRENCY: int = 4
    AGENT_MAX_RETRIES: int = 2
    AGENT_TIMEOUT_SECONDS: float = 60.0
    MAX_CONTEXT_CHARS: int = 16000
    MAX_CONTEXT_FILES: int = 10
    MAX_CONTEXT_SYMBOLS: int = 30

    # Model Routing Configuration (maps specialist to fast vs reasoning tier)
    MODEL_TIER_COMPREHENSION: Literal["fast", "reasoning"] = "fast"
    MODEL_TIER_SECURITY: Literal["fast", "reasoning"] = "reasoning"
    MODEL_TIER_BUG: Literal["fast", "reasoning"] = "reasoning"
    MODEL_TIER_TEST: Literal["fast", "reasoning"] = "fast"
    MODEL_TIER_PERFORMANCE: Literal["fast", "reasoning"] = "reasoning"

    # Token Pricing (USD per 1,000,000 tokens)
    PRICE_PER_MILLION_INPUT_TOKENS_FAST: float = 0.075
    PRICE_PER_MILLION_OUTPUT_TOKENS_FAST: float = 0.30
    PRICE_PER_MILLION_INPUT_TOKENS_REASONING: float = 1.25
    PRICE_PER_MILLION_OUTPUT_TOKENS_REASONING: float = 5.00

    # Phase 4: Adversarial Verification & Execution Sandbox Configuration
    SANDBOX_IMAGE: str = "codeguard-sandbox:latest"
    SANDBOX_CPU_LIMIT: float = 1.0
    SANDBOX_MEMORY_LIMIT: str = "512m"
    SANDBOX_MAX_PROCESSES: int = 64
    SANDBOX_TIMEOUT_SECONDS: int = 30
    SANDBOX_MAX_OUTPUT_BYTES: int = 65536
    MAX_CONCURRENT_VALIDATIONS: int = 4
    SANDBOX_ALLOWLIST_COMMANDS: list[str] = [
        "pytest",
        "python -m pytest",
        "npm test",
        "npm run test",
        "ruff check",
        "eslint",
    ]
    STATIC_ANALYZERS_ENABLED: list[str] = ["ruff", "eslint"]
    JUDGE_MODEL_TIER: Literal["fast", "reasoning"] = "reasoning"
    JUDGE_MAX_RETRIES: int = 2

    # Phase 5: MCP Gateway & Human Approval Configuration
    MCP_SERVER_URL: str = "http://localhost:8001"
    MCP_SERVICE_TOKEN: str = "dev-mcp-service-token"
    APPROVAL_EXPIRY_MINUTES_DEFAULT: int = 60

    # Security & Auth
    DEV_AUTH_BYPASS: bool = True
    DEV_AUTH_TOKEN: str = "codeguard-dev-token"
    SECRET_KEY: str = "insecure-dev-secret-key-change-in-production-32bytes"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(i) for i in v]
        return ["http://localhost:3000"]

    @field_validator("APP_ENV")
    @classmethod
    def validate_production_config(cls, env: str, info: object) -> str:
        # Note: Validation for strict production flags will run on instantiation
        return env

    def model_post_init(self, __context: object) -> None:
        """Validate production invariants."""
        if self.APP_ENV == "production":
            errors = []
            if "*" in self.CORS_ORIGINS:
                errors.append("Wildcard CORS (*) is forbidden in production.")
            if not self.GITHUB_PRIVATE_KEY:
                errors.append("GITHUB_PRIVATE_KEY must be configured in production.")
            if self.GITHUB_WEBHOOK_SECRET in ("dev-webhook-secret", ""):
                errors.append("Production GITHUB_WEBHOOK_SECRET must be configured.")
            if self.SECRET_KEY.startswith("insecure-dev"):
                errors.append("Production SECRET_KEY must be securely configured.")
            if self.DEV_AUTH_BYPASS:
                errors.append("DEV_AUTH_BYPASS cannot be True in production.")
            if self.LLM_PROVIDER == "mock":
                errors.append("LLM_PROVIDER cannot be 'mock' in production.")
            if not self.GEMINI_API_KEY:
                errors.append("GEMINI_API_KEY must be configured in production.")
            if self.MCP_SERVICE_TOKEN in ("dev-mcp-service-token", ""):
                errors.append("Production MCP_SERVICE_TOKEN must be securely configured.")
            if "localhost" in self.DATABASE_URL or "codeguard_secret" in self.DATABASE_URL:
                errors.append("Production DATABASE_URL must not use local default credentials or localhost.")
            if errors:
                raise ValueError(
                    f"Production configuration validation failed: {'; '.join(errors)}"
                )


settings = Settings()
