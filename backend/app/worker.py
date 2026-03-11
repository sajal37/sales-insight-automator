"""Background worker — processes upload jobs from Redis queue."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
import time

# Fix import path when running as standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.logging_config import setup_logging, get_logger
from app.database import init_db, update_job
from app.services.parser import parse_file
from app.services.analyzer_v2 import analyze, get_top_rows_csv, stats_to_json
from app.services.charts import generate_charts
from app.services.llm_v2 import generate_summary
from app.services.mailer_v2 import send_summary_email

setup_logging()
logger = get_logger(__name__)

QUEUE_NAME = "sia:jobs"
_shutdown = False


def _handle_signal(signum: int, frame: object) -> None:
    global _shutdown
    _shutdown = True
    logger.info("Shutdown signal received, finishing current job...")


async def process_job(job_data: dict) -> None:
    """Execute the full pipeline for a single job."""
    job_id = job_data["job_id"]
    log = get_logger(__name__, job_id=job_id)

    update_job(job_id, status="processing", started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    log.info("Processing started")

    try:
        # Stage 1: Parse file
        log.info("Parsing file: %s", job_data["filename"])
        content = bytes.fromhex(job_data["file_hex"])
        df = parse_file(content, job_data["filename"])
        rows = len(df)
        log.info("Parsed %d rows", rows)

        # Stage 2: Analyze
        log.info("Running analytics")
        stats = analyze(df)
        stats_json_str = stats_to_json(stats)
        top_csv = get_top_rows_csv(df, n=3)

        # Stage 3: Generate charts
        log.info("Generating charts")
        chart_paths = generate_charts(stats, job_id)

        # Stage 4: Generate LLM summary
        log.info("Generating LLM summary")
        llm_start = time.perf_counter()
        brief = await generate_summary(stats, top_rows_csv=top_csv)
        llm_latency = (time.perf_counter() - llm_start) * 1000
        provider_used = brief.get("_meta", {}).get("provider", "unknown")
        log.info("LLM summary generated via %s in %.0fms", provider_used, llm_latency)

        # Stage 5: Send email
        log.info("Sending email to %s", job_data["to_email"])
        email_result = await send_summary_email(
            to_email=job_data["to_email"],
            brief=brief,
            subject=job_data.get("subject", "Sales Insight Brief — Rabbitt AI"),
            chart_paths=chart_paths,
        )
        email_id = email_result.get("id")
        log.info("Email sent, id=%s", email_id)

        # Persist results
        update_job(
            job_id,
            status="completed",
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            rows_processed=rows,
            analytics_json=stats_json_str,
            llm_summary=json.dumps(brief, default=str),
            llm_provider_used=provider_used,
            llm_latency_ms=round(llm_latency, 1),
            email_status="sent",
            email_id=str(email_id) if email_id else None,
            chart_paths=json.dumps(chart_paths),
        )
        log.info("Job completed successfully")

    except Exception as err:
        log.error("Job failed: %s", err, exc_info=True)
        update_job(
            job_id,
            status="failed",
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            error=str(err),
        )


async def worker_loop() -> None:
    """Main worker loop — poll Redis for jobs."""
    import redis

    r = redis.from_url(settings.redis_url, decode_responses=True)
    logger.info("Worker started, listening on queue '%s' (redis=%s)", QUEUE_NAME, settings.redis_url)

    while not _shutdown:
        # BLPOP with 2s timeout to allow shutdown checks
        result = r.blpop(QUEUE_NAME, timeout=2)
        if result is None:
            continue
        _queue_name, raw = result
        try:
            job_data = json.loads(raw)
            await process_job(job_data)
        except json.JSONDecodeError:
            logger.error("Invalid job payload (not JSON)")
        except Exception:
            logger.exception("Unexpected error processing job")


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    init_db()
    asyncio.run(worker_loop())


if __name__ == "__main__":
    main()
