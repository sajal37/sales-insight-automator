"""Request / response schemas for the API."""

from pydantic import BaseModel, EmailStr, Field
from typing import Any


class UploadResponse(BaseModel):
    """Response from the upload & analyze endpoint."""
    success: bool = True
    summary: str = Field(..., description="AI-generated executive brief in Markdown")
    stats: dict = Field(..., description="Pre-computed statistics used for analysis")
    rows_processed: int = Field(..., description="Number of data rows processed")


class JobCreatedResponse(BaseModel):
    """Response when a job is enqueued asynchronously."""
    success: bool = True
    job_id: str = Field(..., description="Unique job identifier", examples=["a1b2c3d4"])
    status: str = Field("pending", description="Initial job status")
    status_url: str = Field(..., description="URL to poll for job status", examples=["/api/v1/jobs/a1b2c3d4"])


class JobStatusResponse(BaseModel):
    """Response from the job-status endpoint."""
    job_id: str
    status: str = Field(..., description="pending | processing | completed | failed")
    filename: str | None = None
    to_email: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    rows_processed: int | None = None
    analytics: dict[str, Any] | None = Field(None, description="Structured analytics (when completed)")
    llm_summary: dict | None = Field(None, description="Structured LLM brief (when completed)")
    llm_provider_used: str | None = None
    llm_latency_ms: float | None = None
    email_status: str | None = None
    email_id: str | None = None
    error: str | None = Field(None, description="Error message if job failed")


class LLMBriefResponse(BaseModel):
    """Structured LLM response schema."""
    executive_summary: str
    key_trends: list[str]
    regional_analysis: str
    product_insights: str
    anomalies: list[str]
    recommendations: list[str]


class SendRequest(BaseModel):
    """Request body to send a summary via email."""
    to_email: EmailStr = Field(..., description="Recipient email address")
    summary: str = Field(..., description="Markdown summary to send")
    subject: str = Field(
        "Q1 2026 Sales Insight Brief — Rabbitt AI",
        description="Email subject line",
    )


class SendResponse(BaseModel):
    """Response from the email send endpoint."""
    success: bool = True
    message: str = "Email sent successfully"
    email_id: str | None = Field(None, description="Resend email ID")


class AnalyzeAndSendRequest(BaseModel):
    """Request body for the all-in-one endpoint (used with form data)."""
    to_email: EmailStr
    subject: str = "Q1 2026 Sales Insight Brief — Rabbitt AI"


class AnalyzeAndSendResponse(BaseModel):
    """Response from the all-in-one analyze-and-send endpoint."""
    success: bool = True
    summary: str
    stats: dict
    rows_processed: int
    email_sent: bool = True
    email_id: str | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""
    success: bool = False
    detail: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    service: str = "sales-insight-automator"
    version: str = "2.0.0"
    redis: str = Field("unknown", description="Redis connectivity status")
    database: str = Field("ok", description="Database status")
