"""Sales Insight Automator — FastAPI application entry point."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware.rate_limit import limiter
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import health, upload

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ──
app = FastAPI(
    title="Sales Insight Automator API",
    description=(
        "🐇 **Rabbitt AI** — Upload sales data files and receive AI-generated "
        "executive briefs delivered directly to your inbox.\n\n"
        "### Authentication\n"
        "All endpoints (except `/health` and docs) require an `X-API-Key` header.\n\n"
        "### Rate Limits\n"
        f"Default: `{settings.rate_limit}` per IP address."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    contact={
        "name": "Rabbitt AI Engineering",
        "email": "engineering@rabbittai.com",
    },
)

# ── Middleware (order matters — outermost first) ──
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)

# ── Rate limiter ──
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Routers ──
app.include_router(health.router, prefix="/api/v1")
app.include_router(upload.router)


# ── Global exception handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "An internal error occurred."},
    )


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "Sales Insight Automator",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
