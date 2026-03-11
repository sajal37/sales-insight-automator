"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # API Security
    api_key: str = Field(..., description="Secret API key for endpoint authentication")
    allowed_origins: str = Field(
        "http://localhost:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # LLM Provider
    llm_provider: str = Field("gemini", description="Primary LLM provider: gemini | groq")
    llm_fallback_provider: str = Field("groq", description="Fallback LLM provider: gemini | groq")
    gemini_api_key: str = Field("", description="Google Gemini API key")
    groq_api_key: str = Field("", description="Groq API key")

    # Email (Resend primary)
    resend_api_key: str = Field("", description="Resend API key for email delivery")
    from_email: str = Field(
        "Sales Automator <onboarding@resend.dev>",
        description="Sender email address",
    )
    # SMTP fallback
    smtp_host: str = Field("", description="SMTP fallback host")
    smtp_port: int = Field(587, description="SMTP fallback port")
    smtp_user: str = Field("", description="SMTP fallback username")
    smtp_password: str = Field("", description="SMTP fallback password")

    # Upload Limits
    max_upload_size_mb: int = Field(50, description="Maximum upload file size in MB")
    max_rows: int = Field(100_000, description="Maximum number of rows to process")

    # Rate Limiting
    rate_limit: str = Field("10/minute", description="Default rate limit per IP")
    upload_rate_limit: str = Field("5/minute", description="Upload rate limit per IP")

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", description="Redis connection URL")

    # Database
    database_url: str = Field("sqlite:///./jobs.db", description="SQLite database path")

    # Charts
    chart_dir: str = Field("/tmp/sia_charts", description="Directory for generated chart PNGs")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
