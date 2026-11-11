"""
FastAPI application entry point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting Muscle Training API in {settings.python_env} mode")
    logger.info(f"Agent features enabled: {settings.enable_agent}")
    logger.info(f"Knowledge import enabled: {settings.enable_knowledge_import}")

    yield

    # Shutdown
    logger.info("Shutting down Muscle Training API")


# Create FastAPI application
app = FastAPI(
    title="Muscle Training Agent API",
    description="Private fitness training agent with AI-powered planning and offline sync",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.python_env != "production" else None,
    redoc_url="/redoc" if settings.python_env != "production" else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "environment": settings.python_env,
            "features": {
                "signup": settings.enable_signup,
                "agent": settings.enable_agent,
                "knowledge_import": settings.enable_knowledge_import,
                "weekly_review": settings.enable_weekly_review,
            },
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Muscle Training Agent API",
        "version": "0.1.0",
        "docs": "/docs" if settings.python_env != "production" else None,
    }
