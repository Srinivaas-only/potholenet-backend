import logging
from typing import Optional
import time

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session

from app.models.schemas import DetectionResponse, DetectionCategory, ErrorResponse, DualModeDetectionResponse
from app.services.detector import annotate_detections, get_detector
from app import main as app_main
from app.database import get_db
from app.models.db_models import PotholeDetection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["detection"])


@router.post(
    "/detect",
    response_model=DetectionResponse,
    summary="Run pothole and object detection on an uploaded image",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid image"},
        500: {"model": ErrorResponse, "description": "Model inference error"},
    },
)
async def detect_objects(image: UploadFile = File(...)):
    """
    Accept a JPEG/PNG image via multipart form upload and run:
    1. Roboflow pothole detection model
    2. YOLOv8n COCO object detection

    Returns structured detection results with pothole, human, vehicle, and animal
    categories, plus an alert string.
    """
    # Validate file type
    if image.content_type and image.content_type not in (
        "image/jpeg",
        "image/png",
        "image/jpg",
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image format: {image.content_type}. Accepted: JPEG, PNG.",
        )

    detector = get_detector()

    try:
        image_bytes = await image.read()

        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty image file received.")

        result = detector.run_detection(image_bytes)
        return DetectionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Detection endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Model inference failed: {str(e)}"
        )


@router.post(
    "/detect/dual-mode",
    response_model=DualModeDetectionResponse,
    summary="Dual-mode detection: REVERSE (YOLO only) vs DRIVING (Pothole + YOLO)",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid image or parameters"},
        500: {"model": ErrorResponse, "description": "Model inference error"},
    },
)
async def detect_dual_mode(
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Dual-mode detection endpoint. Mode is determined purely by phone GPS speed.

    **REVERSE Mode** (velocity_kmh <= 10):
    - YOLOv8 runs to detect humans / vehicles / animals behind the car
    - Pothole detection skipped (irrelevant at parking speed)
    - The raw rear-view video stream itself is separately served ESP32 -> phone
      over the AP, so the display still works when phone has no mobile data;
      these YOLO alerts only fire when the phone has internet to reach this backend.

    **DRIVING Mode** (velocity_kmh > 10):
    - Roboflow pothole detection + YOLOv8 object detection
    - Full hazard detection at road speeds

    Fallback: if no GPS speed has been pushed via /location/update, defaults to DRIVING.
    """
    # Validate file type
    if image.content_type and image.content_type not in (
        "image/jpeg",
        "image/png",
        "image/jpg",
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image format: {image.content_type}. Accepted: JPEG, PNG.",
        )

    detector = get_detector()

    try:
        image_bytes = await image.read()

        if len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Empty image file received.")

        # Push the raw frame to the stream cache the moment it arrives, so /stream
        # sees the frame ~hundreds of ms before detection finishes annotating it.
        app_main.frame_state["jpeg"] = image_bytes
        app_main.frame_state["timestamp"] = time.time()

        # Pick mode from phone GPS speed: <=10 km/h is REVERSE, faster is DRIVING.
        velocity_kmh = app_main.gps_state.get("velocity_kmh")
        if velocity_kmh is None:
            mode = "driving"
            logger.warning("No phone GPS speed available, defaulting to DRIVING mode")
        elif velocity_kmh <= 10:
            mode = "reverse"
        else:
            mode = "driving"
        logger.info(f"Mode={mode} (velocity_kmh={velocity_kmh})")

        result = detector.run_detection_dual_mode(
            image_bytes, mode=mode, velocity_kmh=velocity_kmh
        )

        # Cache an annotated copy of the frame for /stream and /latest-frame.jpg.
        app_main.frame_state["jpeg"] = annotate_detections(image_bytes, result)
        app_main.frame_state["timestamp"] = time.time()

        # Save pothole detection to database if potholes detected
        if result.get("pothole", {}).get("detected"):
            save_pothole_detection(db, result, velocity_kmh)

        return DualModeDetectionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dual-mode detection endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Model inference failed: {str(e)}"
        )




def save_pothole_detection(db: Session, detection_result: dict, velocity_kmh: Optional[float]):
    """
    Save pothole detection to database with location and time.
    
    Args:
        db: Database session
        detection_result: Detection result from run_detection_dual_mode()
        velocity_kmh: Current vehicle velocity
    """
    try:
        # Get phone GPS location
        latitude = app_main.gps_state.get("latitude")
        longitude = app_main.gps_state.get("longitude")
        mode = detection_result.get("mode", "DRIVING")
        
        # Get pothole confidence (average of all detected potholes)
        pothole_details = detection_result.get("pothole", {}).get("details", [])
        confidence = 0.0
        if pothole_details:
            confidence = sum([p.get("confidence", 0) for p in pothole_details]) / len(pothole_details)
        
        # Create database record
        pothole_record = PotholeDetection(
            latitude=latitude,
            longitude=longitude,
            confidence=confidence,
            velocity_kmh=velocity_kmh,
            mode=mode,
            pothole_count=detection_result.get("pothole", {}).get("count", 0)
        )
        
        db.add(pothole_record)
        db.commit()
        
        logger.info(
            f"Pothole detection saved: "
            f"id={pothole_record.id}, "
            f"location=({latitude}, {longitude}), "
            f"confidence={confidence:.2f}, "
            f"velocity={velocity_kmh} km/h"
        )
        
    except Exception as e:
        logger.error(f"Failed to save pothole detection: {e}", exc_info=True)
        db.rollback()