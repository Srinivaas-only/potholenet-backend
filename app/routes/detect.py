import logging
from typing import Optional
import time

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from app.models.schemas import DetectionResponse, DetectionCategory, ErrorResponse, DualModeDetectionResponse
from app.services.detector import get_detector
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
    mode: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """
    Dual-mode detection endpoint optimized for reverse and driving scenarios.
    
    **REVERSE Mode** (Low latency <100ms):
    - YOLOv8 only: detects humans, vehicles, animals
    - Skips pothole detection for speed
    - Useful for backing up or maneuvering
    
    **DRIVING Mode** (Balanced <500ms):
    - Roboflow pothole detection + YOLOv8 object detection
    - Full accuracy for hazard detection
    - Auto-detects reverse if velocity < 0 km/h
    
    Mode Detection:
    - If mode="reverse" explicitly: use REVERSE
    - If mode="driving" explicitly: use DRIVING
    - If mode=None: auto-detect from phone GPS speed
      - velocity_kmh < 0: REVERSE
      - velocity_kmh >= 0: DRIVING
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

        # Get phone GPS speed
        velocity_kmh = app_main.gps_state.get("velocity_kmh")
        
        # Auto-detect mode from phone GPS speed if not explicitly provided
        if mode is None:
            if velocity_kmh is not None:
                mode = "reverse" if velocity_kmh < 0 else "driving"
                logger.info(f"Auto-detected mode={mode} from phone GPS speed={velocity_kmh} km/h")
            else:
                mode = "driving"
                logger.warning("No phone GPS speed available, defaulting to DRIVING mode")

        result = detector.run_detection_dual_mode(
            image_bytes, mode=mode, velocity_kmh=velocity_kmh
        )
        
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


@router.post("/location/update", tags=["gps"])
async def update_phone_location(velocity_kmh: float = Form(...), latitude: Optional[float] = Form(None), longitude: Optional[float] = Form(None)):
    """
    Phone app sends current velocity and GPS location to update detection mode.
    
    Called by phone GPS module:
    - velocity_kmh > 0: Forward (DRIVING mode)
    - velocity_kmh < 0: Reverse (REVERSE mode)  
    - velocity_kmh = 0: Stopped (defaults to DRIVING)
    - latitude: Phone GPS latitude (-90 to 90)
    - longitude: Phone GPS longitude (-180 to 180)
    
    Location is used to record where potholes are detected.
    
    Example (phone app sends this every GPS update):
    ```
    POST /location/update
    Form Data: velocity_kmh=45.5, latitude=3.1234, longitude=101.5678
    ```
    """
    app_main.gps_state["velocity_kmh"] = velocity_kmh
    app_main.gps_state["latitude"] = latitude
    app_main.gps_state["longitude"] = longitude
    app_main.gps_state["last_update"] = time.time()
    
    logger.info(f"Phone GPS updated: {velocity_kmh} km/h at ({latitude}, {longitude})")
    
    return {
        "status": "ok",
        "velocity_kmh": velocity_kmh,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": app_main.gps_state["last_update"]
    }


@router.get("/location/current-speed", tags=["gps"])
async def get_current_speed():
    """
    Get the latest phone GPS speed and location.
    
    Returns:
    - velocity_kmh: Latest speed (None if not updated yet)
    - latitude: Latest latitude (None if not available)
    - longitude: Latest longitude (None if not available)
    - last_update: Timestamp of last update
    
    Used by ESP32-CAM or other clients to check current speed and location.
    """
    return {
        "velocity_kmh": app_main.gps_state.get("velocity_kmh"),
        "latitude": app_main.gps_state.get("latitude"),
        "longitude": app_main.gps_state.get("longitude"),
        "last_update": app_main.gps_state.get("last_update"),
    }


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