import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.schemas import (
    ErrorResponse,
    FalseNegativeResponse,
    HazardResponse,
    ReportCreate,
    ReportResponse,
)
from app.services.hazard_store import create_or_update_report, query_hazards, save_false_negative

logger = logging.getLogger(__name__)

router = APIRouter(tags=["reports"])


@router.post(
    "/reports",
    response_model=ReportResponse,
    summary="Submit a pothole sighting to the shared database",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Database error"},
    },
)
async def submit_report(report: ReportCreate, db: Session = Depends(get_db)):
    """
    Submit a confirmed pothole sighting.

    If a report already exists within 5 meters and 30 days, the existing
    report's severity_score is incremented instead of creating a new record.
    """
    try:
        result = create_or_update_report(
            db=db,
            latitude=report.latitude,
            longitude=report.longitude,
            confidence=report.confidence,
            vehicle_type=report.vehicle_type.value,
            thumbnail_base64=report.thumbnail_base64,
        )
        return ReportResponse(**result)
    except Exception as e:
        logger.error(f"Report submission error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create report: {str(e)}")


@router.get(
    "/hazards",
    response_model=HazardResponse,
    summary="Query pothole hazards near a location",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
    },
)
async def get_hazards(
    lat: float = Query(..., ge=-90, le=90, description="Driver's current latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Driver's current longitude"),
    radius_m: int = Query(2000, ge=1, le=5000, description="Search radius in meters"),
    min_severity: int = Query(1, ge=1, description="Minimum severity score"),
    db: Session = Depends(get_db),
):
    """
    Query for pothole hazards near the driver's current location.

    Returns hazards within the specified radius, filtered by severity and
    freshness (90-day expiry). Sorted by distance, limited to 50 results.
    """
    try:
        result = query_hazards(
            db=db,
            lat=lat,
            lng=lng,
            radius_m=radius_m,
            min_severity=min_severity,
        )
        return HazardResponse(**result)
    except Exception as e:
        logger.error(f"Hazard query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to query hazards: {str(e)}")


@router.post(
    "/reports/false-negative",
    response_model=FalseNegativeResponse,
    summary="Submit missed pothole frames for future retraining",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def submit_false_negative(
    latitude: float = Form(..., description="Latitude of the sighting"),
    longitude: float = Form(..., description="Longitude of the sighting"),
    images: List[UploadFile] = File(..., description="One or more image frames"),
    db: Session = Depends(get_db),
):
    """
    Submit frames from a 'report missed pothole' action.

    Accepts one or more image files along with the location. Images are saved
    to the retraining queue for future model improvement.
    """
    # Validate coordinates
    if not (-90 <= latitude <= 90):
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
    if not (-180 <= longitude <= 180):
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")

    if not images:
        raise HTTPException(status_code=400, detail="At least one image is required")

    try:
        result = save_false_negative(
            db=db,
            latitude=latitude,
            longitude=longitude,
            image_files=images,
        )
        return FalseNegativeResponse(**result)
    except Exception as e:
        logger.error(f"False negative submission error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to save false negative: {str(e)}"
        )