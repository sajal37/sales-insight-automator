"""Health check router with Redis and DB connectivity."""

from fastapi import APIRouter

from app.config import settings
from app.schemas.models import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the health status of the API including Redis and database connectivity.",
)
async def health_check():
    redis_status = "not_configured"
    if settings.redis_url:
        try:
            import redis
            r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
            redis_status = "connected"
        except Exception:
            redis_status = "unavailable"

    db_status = "ok"
    try:
        from app.database import get_job
        get_job("__health_check__")
    except Exception:
        db_status = "error"

    overall = "healthy"
    if redis_status == "unavailable":
        overall = "degraded"

    return HealthResponse(status=overall, redis=redis_status, database=db_status)
