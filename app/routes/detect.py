import logging
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Query

from app.models.schemas import DetectionResponse, DetectionCategory, ErrorResponse, DualModeDetectionResponse
from app.services.detector import get_detector

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
    mode: Optional[str] = Query("driving", regex="^(reverse|driving)$"),
    velocity_kmh: Optional[float] = Query(None, ge=-150, le=250),
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
    
    Parameters:
    - mode: "reverse" or "driving" (default: "driving")
    - velocity_kmh: Current vehicle velocity (optional, auto-detects if negative)
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

        result = detector.run_detection_dual_mode(
            image_bytes, mode=mode, velocity_kmh=velocity_kmh
        )
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