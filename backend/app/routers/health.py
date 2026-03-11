"""Health check router."""

from fastapi import APIRouter

from app.schemas.models import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the health status of the API. Used by Docker healthchecks and monitoring.",
)
async def health_check():
    return HealthResponse()
