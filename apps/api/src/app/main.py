"""
FastAPI application entry point (plan §2.3 / §6.1 / §11.3)

- API lives under /api/v1.
- /health/live is process health; /health/ready checks DB + config.
- Migrations are an explicit deploy step, never run at startup.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.errors import api_error_handler, http_error_handler, validation_error_handler
from app.api.middleware import RequestContextMiddleware
from app.api.router import api_router
from app.config import get_settings
from app.db.session import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Muscle Training API in %s mode", settings.python_env)
    logger.info("Agent features enabled: %s", settings.enable_agent)
    logger.info("Knowledge import enabled: %s", settings.enable_knowledge_import)
    yield
    logger.info("Shutting down Muscle Training API")
    await engine.dispose()


app = FastAPI(
    title="Muscle Training Agent API",
    description="Private fitness training agent with AI-powered planning and offline sync",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.python_env != "production" else None,
    redoc_url="/redoc" if settings.python_env != "production" else None,
)

# CORS for the dev Vite server; production is same-origin behind Caddy
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request id + Origin enforcement
app.add_middleware(RequestContextMiddleware)

# Unified error envelope
app.add_exception_handler(RequestValidationError, validation_error_handler)
from app.api.errors import ApiError  # noqa: E402

app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(Exception, http_error_handler)

# API under /api/v1 (plan §6.1)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health/live")
async def health_live():
    """Process health: always cheap."""
    return {"status": "alive"}


@app.get("/health/ready")
async def health_ready():
    """Readiness: database reachable and config valid."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - depends on deployment
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "down", "detail": str(exc)[:200]},
        )
    return {
        "status": "ready",
        "environment": settings.python_env,
        "features": {
            "signup": settings.enable_signup,
            "agent": settings.enable_agent and bool(settings.dashscope_api_key),
            "knowledge_import": settings.enable_knowledge_import,
            "weekly_review": settings.enable_weekly_review,
        },
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Muscle Training Agent API",
        "version": "0.2.0",
        "docs": "/docs" if settings.python_env != "production" else None,
    }
