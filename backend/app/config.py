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
    llm_provider: str = Field("gemini", description="LLM provider: gemini | groq")
    gemini_api_key: str = Field("", description="Google Gemini API key")
    groq_api_key: str = Field("", description="Groq API key")

    # Email
    resend_api_key: str = Field("", description="Resend API key for email delivery")
    from_email: str = Field(
        "Sales Automator <onboarding@resend.dev>",
        description="Sender email address",
    )

    # Upload Limits
    max_upload_size_mb: int = Field(50, description="Maximum upload file size in MB")
    max_rows: int = Field(100_000, description="Maximum number of rows to process")

    # Rate Limiting
    rate_limit: str = Field("10/minute", description="Rate limit per IP")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
