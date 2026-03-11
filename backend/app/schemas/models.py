"""Request / response schemas for the API."""

from pydantic import BaseModel, EmailStr, Field


class UploadResponse(BaseModel):
    """Response from the upload & analyze endpoint."""
    success: bool = True
    summary: str = Field(..., description="AI-generated executive brief in Markdown")
    stats: dict = Field(..., description="Pre-computed statistics used for analysis")
    rows_processed: int = Field(..., description="Number of data rows processed")


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
    version: str = "1.0.0"
