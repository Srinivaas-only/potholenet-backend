import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import HealthResponse, ModelsLoaded
from app.services.detector import get_detector
from app.services.hazard_store import get_total_reports_count

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Track server start time
_start_time = time.time()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check server health and model status",
)
async def health_check(db: Session = Depends(get_db)):
    """
    Returns server status, model loading state, total report count,
    and server uptime in seconds.
    """
    detector = get_detector()

    try:
        reports_count = get_total_reports_count(db)
    except Exception:
        reports_count = 0

    return HealthResponse(
        status="ok",
        models_loaded=ModelsLoaded(
            pothole=detector.models_loaded["pothole"],
            yolov8=detector.models_loaded["yolov8"],
        ),
        reports_count=reports_count,
        uptime_seconds=round(time.time() - _start_time, 2),
    )