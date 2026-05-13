import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import create_tables
from app.routes import detect, reports, health
from app.services.detector import get_detector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="PotholeNet API",
    description="Cloud backend for PotholeNet — crowdsourced road hazard intelligence",
    version="1.0.0",
)

# CORS middleware — allow all origins for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Load ML models and create database tables on server startup."""
    logger.info("Starting PotholeNet backend...")

    # Create database tables
    logger.info("Creating database tables...")
    create_tables()
    logger.info("Database tables ready")

    # Load ML models once
    logger.info("Loading ML models...")
    detector = get_detector()
    detector.load_models()
    logger.info(
        f"Models loaded — pothole: {detector.models_loaded['pothole']}, "
        f"yolov8: {detector.models_loaded['yolov8']}"
    )

    logger.info("PotholeNet backend started successfully")


# Include route routers
app.include_router(detect.router)
app.include_router(reports.router)
app.include_router(health.router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint — redirects to API docs."""
    return {
        "message": "PotholeNet API is running",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )