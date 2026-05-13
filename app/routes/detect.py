import logging

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.models.schemas import DetectionResponse, DetectionCategory, ErrorResponse
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