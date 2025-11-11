"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.api import health, robots, opportunities, niches, settings as settings_api, jobs, events, validation
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


# Create FastAPI app (with redirect_slashes disabled at router level)
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Automated YouTube topic discovery using 4-robot microservice architecture",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure app router to not redirect trailing slashes
app.router.redirect_slashes = False

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(robots.router, prefix="/api/robots", tags=["Robots"])
app.include_router(opportunities.router, prefix="/api/opportunities", tags=["Opportunities"])
app.include_router(niches.router, prefix="/api/niches", tags=["Niches"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["Settings"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(events.router, prefix="/api/events", tags=["Events"])
app.include_router(validation.router, prefix="/api/validation", tags=["Validation"])


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {'DEBUG' if settings.DEBUG else 'PRODUCTION'}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    logger.info("Shutting down application")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
