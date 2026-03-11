"""Upload, analyze, and email routers — the core API surface."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import EmailStr

from app.middleware.auth import verify_api_key
from app.middleware.rate_limit import limiter
from app.services.parser import parse_file, ParserError
from app.services.analyzer import analyze, stats_to_json
from app.services.llm import generate_summary
from app.services.mailer import send_summary_email
from app.schemas.models import (
    UploadResponse,
    SendRequest,
    SendResponse,
    AnalyzeAndSendResponse,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["Sales Insight"],
    dependencies=[Depends(verify_api_key)],
    responses={
        401: {"model": ErrorResponse, "description": "Missing API key"},
        403: {"model": ErrorResponse, "description": "Invalid API key"},
        429: {"description": "Rate limit exceeded"},
    },
)


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload & Analyze",
    description=(
        "Upload a `.csv` or `.xlsx` sales data file. "
        "The file is parsed, statistics are computed, and an AI "
        "executive brief is generated and returned."
    ),
    responses={400: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
async def upload_and_analyze(
    request: Request,
    file: UploadFile = File(..., description="Sales data file (.csv or .xlsx)"),
    _key: str = Depends(verify_api_key),
):
    # ── Parse ──
    try:
        content = await file.read()
        df = parse_file(content, file.filename or "upload.csv")
    except ParserError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Unexpected parse error")
        raise HTTPException(status_code=400, detail="Failed to parse the uploaded file.")

    # ── Analyze ──
    stats = analyze(df)

    # ── Generate AI summary ──
    try:
        summary = await generate_summary(stats)
    except RuntimeError as exc:
        logger.warning("LLM quota/rate error: %s", exc)
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception as exc:
        logger.exception("LLM generation failed")
        raise HTTPException(status_code=502, detail="AI summary generation failed. Please try again.")

    return UploadResponse(
        summary=summary,
        stats=stats,
        rows_processed=len(df),
    )


@router.post(
    "/send",
    response_model=SendResponse,
    summary="Send Summary Email",
    description="Send a previously generated summary to an email address.",
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
@limiter.limit("10/minute")
async def send_email(
    request: Request,
    body: SendRequest,
    _key: str = Depends(verify_api_key),
):
    try:
        result = await send_summary_email(
            to_email=body.to_email,
            summary_markdown=body.summary,
            subject=body.subject,
        )
        return SendResponse(
            email_id=result.get("id") if isinstance(result, dict) else getattr(result, "id", None),
        )
    except Exception as exc:
        logger.exception("Email send failed")
        raise HTTPException(status_code=502, detail="Failed to send email. Please check your email configuration.")


@router.post(
    "/analyze-and-send",
    response_model=AnalyzeAndSendResponse,
    summary="Upload, Analyze & Email (All-in-One)",
    description=(
        "Upload a file, generate an AI summary, and send it to the "
        "specified email address — all in a single request."
    ),
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
@limiter.limit("5/minute")
async def analyze_and_send(
    request: Request,
    file: UploadFile = File(..., description="Sales data file (.csv or .xlsx)"),
    to_email: str = Form(..., description="Recipient email address"),
    subject: str = Form("Q1 2026 Sales Insight Brief — Rabbitt AI", description="Email subject line"),
    _key: str = Depends(verify_api_key),
):
    # ── Parse ──
    try:
        content = await file.read()
        df = parse_file(content, file.filename or "upload.csv")
    except ParserError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Unexpected parse error")
        raise HTTPException(status_code=400, detail="Failed to parse the uploaded file.")

    # ── Analyze ──
    stats = analyze(df)

    # ── Generate AI summary ──
    try:
        summary = await generate_summary(stats)
    except RuntimeError as exc:
        logger.warning("LLM quota/rate error: %s", exc)
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception:
        logger.exception("LLM generation failed")
        raise HTTPException(status_code=502, detail="AI summary generation failed.")

    # ── Send email ──
    email_id = None
    email_sent = False
    try:
        result = await send_summary_email(
            to_email=to_email,
            summary_markdown=summary,
            subject=subject,
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        email_sent = True
    except Exception:
        logger.exception("Email send failed")

    return AnalyzeAndSendResponse(
        summary=summary,
        stats=stats,
        rows_processed=len(df),
        email_sent=email_sent,
        email_id=email_id,
    )


# ─── Server-Sent Events endpoint for real-time progress ───


async def _sse_pipeline(content: bytes, filename: str, to_email: str, subject: str) -> AsyncGenerator[str, None]:
    """Run the full pipeline, yielding SSE events at each stage."""

    def _event(stage: str, status: str, data: dict | None = None) -> str:
        payload = {"stage": stage, "status": status}
        if data:
            payload["data"] = data
        return f"data: {json.dumps(payload)}\n\n"

    # Stage 1 — Parsing
    yield _event("parsing", "in-progress")
    try:
        df = parse_file(content, filename)
        yield _event("parsing", "complete", {"rows": len(df)})
    except ParserError as exc:
        yield _event("parsing", "error", {"detail": str(exc)})
        return

    # Stage 2 — Analyzing
    yield _event("analyzing", "in-progress")
    stats = analyze(df)
    yield _event("analyzing", "complete", {"stats": stats})

    # Stage 3 — Generating
    yield _event("generating", "in-progress")
    try:
        summary = await generate_summary(stats)
        yield _event("generating", "complete", {"summary": summary})
    except RuntimeError as exc:
        logger.warning("LLM quota/rate error in SSE: %s", exc)
        yield _event("generating", "error", {"detail": str(exc)})
        return
    except Exception as exc:
        logger.exception("LLM failed in SSE pipeline")
        yield _event("generating", "error", {"detail": "AI generation failed"})
        return

    # Stage 4 — Sending email
    yield _event("sending", "in-progress")
    try:
        result = await send_summary_email(to_email, summary, subject)
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        yield _event("sending", "complete", {"email_id": email_id})
    except Exception:
        logger.exception("Email failed in SSE pipeline")
        yield _event("sending", "error", {"detail": "Email delivery failed"})
        return

    yield _event("done", "complete")


@router.post(
    "/stream",
    summary="Stream Pipeline Progress (SSE)",
    description=(
        "Upload a file and stream real-time progress events via Server-Sent Events. "
        "Each stage (parsing → analyzing → generating → sending) emits a status event."
    ),
)
@limiter.limit("5/minute")
async def stream_pipeline(
    request: Request,
    file: UploadFile = File(...),
    to_email: str = Form(...),
    subject: str = Form("Q1 2026 Sales Insight Brief — Rabbitt AI"),
    _key: str = Depends(verify_api_key),
):
    content = await file.read()
    return StreamingResponse(
        _sse_pipeline(content, file.filename or "upload.csv", to_email, subject),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
