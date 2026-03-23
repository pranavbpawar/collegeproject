"""
TBAPS FastAPI Application
Main application entry point — production hardened
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pythonjsonlogger import jsonlogger
from prometheus_client import make_asgi_app
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import api_router
from app.core.exceptions import TBAPSException


# ── Structured JSON logging ────────────────────────────────────────────────────
def _configure_logging() -> None:
    """Configure structured JSON or plain-text logging based on settings."""
    handler = logging.StreamHandler()
    if settings.LOG_FORMAT == "json":
        formatter = jsonlogger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Suppress noisy third-party loggers in production
    if not settings.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


_configure_logging()
logger = logging.getLogger(__name__)

# ── Rate limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"])


# ── Lifespan ───────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and graceful shutdown."""
    logger.info("Starting TBAPS Backend API", extra={"env": settings.APP_ENV, "debug": settings.DEBUG})

    # Create / verify database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified")

    yield  # ← application runs here

    # Graceful shutdown
    logger.info("Shutting down TBAPS Backend API — draining connections...")
    await engine.dispose()
    logger.info("Database connections closed. Shutdown complete.")


# ── Application factory ────────────────────────────────────────────────────────
app = FastAPI(
    title="TBAPS API",
    description="Trust-Based Adaptive Productivity System — Backend API",
    version="1.0.0",
    docs_url="/api/docs" if not settings.APP_ENV == "production" else None,
    redoc_url="/api/redoc" if not settings.APP_ENV == "production" else None,
    openapi_url="/api/openapi.json" if not settings.APP_ENV == "production" else None,
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — restricted to configured origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ── Request ID middleware ──────────────────────────────────────────────────────
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a unique X-Request-ID to every request for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


# ── API routes ─────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")

# Prometheus metrics (bind to internal port separately in production)
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ── Exception handlers ─────────────────────────────────────────────────────────
@app.exception_handler(TBAPSException)
async def tbaps_exception_handler(request: Request, exc: TBAPSException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": exc.timestamp.isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", exc_info=True, extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": str(exc) if settings.DEBUG else None,
        },
    )


# ── Health endpoints ───────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"], include_in_schema=False)
@app.get("/api/v1/health", tags=["Health"], include_in_schema=False)
async def health_check():
    """Liveness probe — returns 200 if the process is alive."""
    return {"status": "ok", "service": "tbaps-api", "version": "1.0.0"}


@app.get("/readiness", tags=["Health"], include_in_schema=False)
async def readiness_check():
    """
    Readiness probe — checks all critical dependencies.
    Returns 200 only when the service is ready to accept traffic.
    """
    from app.core.cache import redis_client

    checks: dict = {}
    overall = "ready"

    # Database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall = "not_ready"

    # Redis — optional when REDIS_OPTIONAL=True (deployment without Redis)
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        if settings.REDIS_OPTIONAL:
            checks["redis"] = f"degraded: {e}"
            if overall == "ready":
                overall = "degraded"  # Service is usable, just without Redis
        else:
            checks["redis"] = f"error: {e}"
            overall = "not_ready"

    http_status = (
        status.HTTP_200_OK
        if overall in ("ready", "degraded")
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(
        status_code=http_status,
        content={"status": overall, "checks": checks, "service": "tbaps-api"},
    )


@app.get("/health/detailed", tags=["Health"], include_in_schema=False)
async def detailed_health_check():
    """Detailed health — alias for readiness, kept for backwards compatibility."""
    return await readiness_check()


@app.get("/", tags=["Root"], include_in_schema=False)
async def root():
    return {"message": "TBAPS Backend API", "version": "1.0.0", "docs": "/api/docs"}


# ── Dev entrypoint ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
