"""
FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.traces import router as traces_router
from app.config import get_settings
from app.observability.logger import setup_logging, get_logger
from app.observability.middleware import RequestLoggingMiddleware

# Setup logging first
setup_logging()
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="AI Change Impact Analyzer",
    description="Analyze business and policy changes to predict technical, operational, and risk impacts",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(analysis_router)
app.include_router(traces_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "AI Change Impact Analyzer",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    settings = get_settings()
    logger.info(
        "Application started",
        debug=settings.DEBUG,
        log_level=settings.LOG_LEVEL,
        auth_enabled=settings.AUTH_ENABLED
    )
    if not settings.AUTH_ENABLED:
        logger.warning("Authentication is DISABLED - not recommended for production!")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Application shutting down")