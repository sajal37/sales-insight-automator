"""Upload, job management, and email routers — the core API surface."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import EmailStr

from app.config import settings
from app.middleware.auth import verify_api_key
from app.middleware.rate_limit import limiter
from app.services.parser import parse_file, ParserError
from app.services.analyzer_v2 import analyze, get_top_rows_csv, stats_to_json
from app.services.llm_v2 import generate_summary
from app.services.mailer_v2 import send_summary_email
from app.services.charts import generate_charts
from app.database import create_job, get_job, update_job
from app.logging_config import get_logger
from app.schemas.models import (
    UploadResponse,
    JobCreatedResponse,
    JobStatusResponse,
    SendRequest,
    SendResponse,
    AnalyzeAndSendResponse,
    ErrorResponse,
)

logger = get_logger(__name__)

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


def _enqueue_job(job_id: str, file_hex: str, filename: str, to_email: str, subject: str) -> None:
    """Push job payload to Redis queue."""
    import redis
    r = redis.from_url(settings.redis_url, decode_responses=True)
    payload = json.dumps({
        "job_id": job_id,
        "file_hex": file_hex,
        "filename": filename,
        "to_email": to_email,
        "subject": subject,
    })
    r.rpush("sia:jobs", payload)


# ─── Async Upload (returns job_id + status URL) ───


@router.post(
    "/upload",
    response_model=JobCreatedResponse,
    summary="Upload File & Create Job",
    description=(
        "Upload a `.csv` or `.xlsx` sales data file along with a recipient email. "
        "The file is validated immediately, then processing is offloaded to a background worker. "
        "Returns a job ID and status URL for polling."
    ),
    responses={400: {"model": ErrorResponse}},
)
@limiter.limit(settings.upload_rate_limit)
async def upload_and_enqueue(
    request: Request,
    file: UploadFile = File(..., description="Sales data file (.csv or .xlsx)"),
    to_email: str = Form(..., description="Recipient email address"),
    subject: str = Form("Q1 2026 Sales Insight Brief — Rabbitt AI", description="Email subject line"),
    _key: str = Depends(verify_api_key),
):
    # ── Validate file upfront (fast) ──
    content = await file.read()
    filename = file.filename if file.filename else "upload.csv"
    try:
        df = parse_file(content, filename)
    except ParserError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Unexpected parse error")
        raise HTTPException(status_code=400, detail="Failed to parse the uploaded file.")

    # ── Create job record ──
    job_id = uuid.uuid4().hex[:12]
    create_job(job_id=job_id, filename=filename, to_email=to_email, subject=subject)

    # ── Enqueue for background processing ──
    try:
        _enqueue_job(
            job_id=job_id,
            file_hex=content.hex(),
            filename=filename,
            to_email=to_email,
            subject=subject,
        )
    except Exception as exc:
        # Redis unavailable — process synchronously as fallback
        logger.warning("Redis unavailable (%s), processing synchronously", exc)
        await _process_sync(job_id, content, filename, to_email, subject)

    return JobCreatedResponse(
        job_id=job_id,
        status="pending",
        status_url=f"/api/v1/jobs/{job_id}",
    )


async def _process_sync(job_id: str, content: bytes, filename: str, to_email: str, subject: str) -> None:
    """Fallback synchronous processing when Redis is unavailable."""
    import time
    log = get_logger(__name__, job_id=job_id)
    update_job(job_id, status="processing", started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    try:
        df = parse_file(content, filename)
        stats = analyze(df)
        top_csv = get_top_rows_csv(df, n=3)
        chart_paths = generate_charts(stats, job_id)
        brief = await generate_summary(stats, top_rows_csv=top_csv)
        provider_used = brief.get("_meta", {}).get("provider", "unknown")
        email_result = await send_summary_email(
            to_email=to_email, brief=brief, subject=subject, chart_paths=chart_paths,
        )
        update_job(
            job_id,
            status="completed",
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            rows_processed=len(df),
            analytics_json=stats_to_json(stats),
            llm_summary=json.dumps(brief, default=str),
            llm_provider_used=provider_used,
            email_status="sent",
            email_id=str(email_result.get("id", "")),
            chart_paths=json.dumps(chart_paths),
        )
        log.info("Sync processing completed")
    except Exception as err:
        log.error("Sync processing failed: %s", err)
        update_job(job_id, status="failed", error=str(err))


# ─── Job Status Endpoint ───


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Get Job Status",
    description=(
        "Poll the status of a processing job. Returns lifecycle timestamps, "
        "analytics summary (when complete), LLM response, and email delivery status."
    ),
    responses={404: {"model": ErrorResponse}},
)
async def get_job_status(
    job_id: str,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    record = get_job(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    llm_summary = None
    if record.get("llm_summary"):
        try:
            llm_summary = json.loads(record["llm_summary"])
        except (json.JSONDecodeError, TypeError):
            llm_summary = None

    return JobStatusResponse(
        job_id=record["id"],
        status=record["status"],
        filename=record.get("filename"),
        to_email=record.get("to_email"),
        created_at=record.get("created_at"),
        updated_at=record.get("updated_at"),
        started_at=record.get("started_at"),
        completed_at=record.get("completed_at"),
        rows_processed=record.get("rows_processed"),
        analytics=record.get("analytics"),
        llm_summary=llm_summary,
        llm_provider_used=record.get("llm_provider_used"),
        llm_latency_ms=record.get("llm_latency_ms"),
        email_status=record.get("email_status"),
        email_id=record.get("email_id"),
        error=record.get("error"),
    )


# ─── Legacy sync send endpoint ───


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
        brief = {"executive_summary": body.summary, "key_trends": [], "regional_analysis": "",
                 "product_insights": "", "anomalies": [], "recommendations": []}
        result = await send_summary_email(
            to_email=body.to_email,
            brief=brief,
            subject=body.subject,
        )
        return SendResponse(
            email_id=result.get("id") if isinstance(result, dict) else getattr(result, "id", None),
        )
    except Exception as exc:
        logger.exception("Email send failed")
        raise HTTPException(status_code=502, detail=f"Failed to send email: {exc}")


# ─── All-in-one sync endpoint (kept for backward compat) ───


@router.post(
    "/analyze-and-send",
    response_model=AnalyzeAndSendResponse,
    summary="Upload, Analyze & Email (All-in-One, Sync)",
    description=(
        "Upload a file, generate an AI summary, and send it to the "
        "specified email address — all in a single synchronous request."
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
        df = parse_file(content, file.filename if file.filename else "upload.csv")
    except ParserError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        logger.exception("Unexpected parse error")
        raise HTTPException(status_code=400, detail="Failed to parse the uploaded file.")

    # ── Analyze ──
    stats = analyze(df)
    top_csv = get_top_rows_csv(df, n=3)

    # ── Generate charts ──
    job_id = uuid.uuid4().hex[:12]
    chart_paths = generate_charts(stats, job_id)

    # ── Generate AI summary ──
    try:
        brief = await generate_summary(stats, top_rows_csv=top_csv)
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    except Exception:
        logger.exception("LLM generation failed")
        raise HTTPException(status_code=502, detail="AI summary generation failed.")

    # Format summary text from structured brief
    summary_text = brief.get("executive_summary", "")

    # ── Send email ──
    email_id = None
    email_sent = False
    try:
        result = await send_summary_email(
            to_email=to_email, brief=brief, subject=subject, chart_paths=chart_paths,
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        email_sent = True
    except Exception:
        logger.exception("Email send failed")

    return AnalyzeAndSendResponse(
        summary=summary_text,
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

    job_id = uuid.uuid4().hex[:12]
    create_job(job_id=job_id, filename=filename, to_email=to_email, subject=subject)

    # Stage 1 — Parsing
    yield _event("parsing", "in-progress")
    try:
        df = parse_file(content, filename)
        yield _event("parsing", "complete", {"rows": len(df), "job_id": job_id})
    except ParserError as exc:
        yield _event("parsing", "error", {"detail": str(exc)})
        update_job(job_id, status="failed", error=str(exc))
        return

    # Stage 2 — Analyzing
    yield _event("analyzing", "in-progress")
    stats = analyze(df)
    top_csv = get_top_rows_csv(df, n=3)
    yield _event("analyzing", "complete", {"stats": stats})

    # Stage 3 — Charts
    yield _event("charting", "in-progress")
    chart_paths = generate_charts(stats, job_id)
    yield _event("charting", "complete", {"chart_count": len(chart_paths)})

    # Stage 4 — Generating
    yield _event("generating", "in-progress")
    try:
        brief = await generate_summary(stats, top_rows_csv=top_csv)
        yield _event("generating", "complete", {"summary": brief.get("executive_summary", "")})
    except RuntimeError as exc:
        logger.warning("LLM quota/rate error in SSE: %s", exc)
        yield _event("generating", "error", {"detail": str(exc)})
        update_job(job_id, status="failed", error=str(exc))
        return
    except Exception as exc:
        logger.exception("LLM failed in SSE pipeline")
        yield _event("generating", "error", {"detail": "AI generation failed"})
        update_job(job_id, status="failed", error=str(exc))
        return

    # Stage 5 — Sending email
    yield _event("sending", "in-progress")
    try:
        result = await send_summary_email(to_email, brief, subject, chart_paths=chart_paths)
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        yield _event("sending", "complete", {"email_id": email_id})
    except Exception as exc:
        logger.exception("Email failed in SSE pipeline")
        yield _event("sending", "error", {"detail": f"Email delivery failed: {exc}"})
        update_job(job_id, status="failed", error=str(exc))
        return

    update_job(
        job_id,
        status="completed",
        rows_processed=len(df),
        analytics_json=stats_to_json(stats),
        llm_summary=json.dumps(brief, default=str),
        email_status="sent",
        email_id=str(email_id) if email_id else None,
    )
    yield _event("done", "complete", {"job_id": job_id})


@router.post(
    "/stream",
    summary="Stream Pipeline Progress (SSE)",
    description=(
        "Upload a file and stream real-time progress events via Server-Sent Events. "
        "Each stage (parsing → analyzing → charting → generating → sending) emits a status event."
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
        _sse_pipeline(content, file.filename if file.filename else "upload.csv", to_email, subject),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
