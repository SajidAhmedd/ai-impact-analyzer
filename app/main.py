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

    if settings.SEED_SAMPLE_DOCUMENTS:
        seed_sample_documents()


def seed_sample_documents():
    """
    Load the bundled sample documents when the vector store is empty.

    WHY: hosted demos start with fresh, ephemeral storage, so without this
    the agents would have no organizational context to retrieve.
    """
    from app.core.vectorstore import get_collection_stats
    from app.ingestion.processor import process_directory

    try:
        if get_collection_stats().get("count", 0) > 0:
            return
        chunks = process_directory("data/documents", metadata={"department": "demo", "doc_type": "policy"})
        logger.info("Seeded sample documents", chunks=chunks)
    except Exception as e:
        logger.error("Failed to seed sample documents", error=str(e))


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Application shutting down")