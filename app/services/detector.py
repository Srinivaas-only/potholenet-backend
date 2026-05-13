import logging
import os
import tempfile
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

# YOLOv8 target classes and their categories
TARGET_CLASSES: Dict[int, str] = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    15: "cat",
    16: "dog",
    17: "horse",
    18: "sheep",
    19: "cow",
    20: "elephant",
    21: "bear",
}

# Classification categories
HUMAN_CLASSES = {0}
VEHICLE_CLASSES = {1, 2, 3, 5, 7}
ANIMAL_CLASSES = {15, 16, 17, 18, 19, 20, 21}


class Detector:
    """Manages loading and running ML models for pothole and object detection."""

    def __init__(self):
        self.roboflow_model = None
        self.yolo_model = None
        self.models_loaded = {"pothole": False, "yolov8": False}

    def load_models(self) -> None:
        """Load both ML models. Called once at server startup."""
        settings = get_settings()

        # Load Roboflow pothole model
        try:
            from roboflow import Roboflow

            rf = Roboflow(api_key=settings.ROBOFLOW_API_KEY)
            project = rf.workspace(settings.ROBOFLOW_WORKSPACE).project(
                settings.ROBOFLOW_PROJECT
            )
            self.roboflow_model = project.version(
                settings.ROBOFLOW_VERSION
            ).model
            self.models_loaded["pothole"] = True
            logger.info("Roboflow pothole model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Roboflow model: {e}")
            self.models_loaded["pothole"] = False

        # Load YOLOv8n model
        try:
            from ultralytics import YOLO

            self.yolo_model = YOLO("yolov8n.pt")
            self.models_loaded["yolov8"] = True
            logger.info("YOLOv8n model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load YOLOv8n model: {e}")
            self.models_loaded["yolov8"] = False

    def decode_image(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """Decode raw image bytes into an OpenCV numpy array."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return img

    def run_detection(self, image_bytes: bytes) -> dict:
        """
        Run both ML models on the given image bytes.

        Returns a structured detection result dict matching DetectionResponse schema.
        """
        settings = get_settings()

        # Decode image
        img = self.decode_image(image_bytes)
        if img is None:
            raise ValueError("Could not decode image. Ensure it is a valid JPEG/PNG.")

        # Save to temp file for model inference
        temp_fd, temp_path = tempfile.mkstemp(suffix=".jpg")
        try:
            cv2.imwrite(temp_path, img)

            # Run Roboflow pothole detection
            pothole_results = self._run_pothole_detection(
                temp_path, settings.POTHOLE_CONFIDENCE_THRESHOLD
            )

            # Run YOLOv8 object detection
            yolo_results = self._run_yolo_detection(temp_path)

        finally:
            # Clean up temp file
            os.close(temp_fd)
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        # Build alert string
        alerts = []
        if pothole_results["detected"]:
            alerts.append("⚠️ POTHOLE DETECTED")
        if yolo_results["humans"]["detected"]:
            alerts.append("🧍 HUMAN ON ROAD")
        if yolo_results["vehicles"]["detected"]:
            alerts.append("🚗 VEHICLE NEARBY")
        if yolo_results["animals"]["detected"]:
            alerts.append("🐄 ANIMAL ON ROAD")

        alert_str = " | ".join(alerts) if alerts else "✅ ALL CLEAR"

        return {
            "pothole": pothole_results,
            "humans": yolo_results["humans"],
            "vehicles": yolo_results["vehicles"],
            "animals": yolo_results["animals"],
            "alert": alert_str,
        }

    def _run_pothole_detection(self, image_path: str, confidence: int) -> dict:
        """Run Roboflow pothole model on an image file."""
        if not self.models_loaded["pothole"] or self.roboflow_model is None:
            logger.warning("Pothole model not loaded, skipping detection")
            return {"detected": False, "count": 0, "details": []}

        try:
            result_json = self.roboflow_model.predict(image_path, confidence=confidence).json()
            predictions = result_json.get("predictions", [])

            details = []
            for pred in predictions:
                details.append(
                    {
                        "confidence": pred.get("confidence", 0),
                        "x": pred.get("x", 0),
                        "y": pred.get("y", 0),
                        "width": pred.get("width", 0),
                        "height": pred.get("height", 0),
                    }
                )

            return {
                "detected": len(details) > 0,
                "count": len(details),
                "details": details,
            }
        except Exception as e:
            logger.error(f"Pothole detection failed: {e}")
            return {"detected": False, "count": 0, "details": []}

    def _run_yolo_detection(self, image_path: str) -> dict:
        """Run YOLOv8n on an image file and categorize detections."""
        humans = {"detected": False, "count": 0, "details": []}
        vehicles = {"detected": False, "count": 0, "details": []}
        animals = {"detected": False, "count": 0, "details": []}

        if not self.models_loaded["yolov8"] or self.yolo_model is None:
            logger.warning("YOLOv8 model not loaded, skipping detection")
            return {"humans": humans, "vehicles": vehicles, "animals": animals}

        try:
            results = self.yolo_model(image_path, verbose=False)

            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])

                    if class_id not in TARGET_CLASSES:
                        continue

                    label = TARGET_CLASSES[class_id]
                    detail = {"label": label, "confidence": round(confidence, 4)}

                    if class_id in HUMAN_CLASSES:
                        humans["details"].append(detail)
                        humans["count"] += 1
                    elif class_id in VEHICLE_CLASSES:
                        vehicles["details"].append(detail)
                        vehicles["count"] += 1
                    elif class_id in ANIMAL_CLASSES:
                        animals["details"].append(detail)
                        animals["count"] += 1

            humans["detected"] = humans["count"] > 0
            vehicles["detected"] = vehicles["count"] > 0
            animals["detected"] = animals["count"] > 0

        except Exception as e:
            logger.error(f"YOLOv8 detection failed: {e}")

        return {"humans": humans, "vehicles": vehicles, "animals": animals}

    def run_detection_dual_mode(
        self, image_bytes: bytes, mode: str = "driving", velocity_kmh: Optional[float] = None
    ) -> dict:
        """
        Run detection in dual-mode (reverse vs driving).
        
        Args:
            image_bytes: Raw image data
            mode: "reverse" or "driving"
            velocity_kmh: Optional vehicle velocity to auto-detect reverse (if negative)
        
        Returns:
            Detection result optimized for the mode
        """
        # Auto-detect reverse based on velocity if provided
        if velocity_kmh is not None and velocity_kmh < 0:
            mode = "reverse"
            logger.info(f"Auto-detected REVERSE mode (velocity: {velocity_kmh} km/h)")
        
        logger.info(f"Running {mode.upper()} detection")
        
        # Decode image
        img = self.decode_image(image_bytes)
        if img is None:
            raise ValueError("Could not decode image. Ensure it is a valid JPEG/PNG.")

        # Save to temp file for model inference
        temp_fd, temp_path = tempfile.mkstemp(suffix=".jpg")
        try:
            cv2.imwrite(temp_path, img)

            if mode.lower() == "reverse":
                # REVERSE MODE: Fast YOLO-only detection (<100ms)
                logger.debug("REVERSE mode: Running YOLO only (lightweight)")
                yolo_results = self._run_yolo_detection(temp_path)
                
                # Skip pothole detection in reverse
                pothole_results = {"detected": False, "count": 0, "details": []}
                
            else:  # driving mode
                # DRIVING MODE: Full detection with Roboflow + YOLO (<500ms)
                logger.debug("DRIVING mode: Running Roboflow + YOLO (full accuracy)")
                settings = get_settings()
                pothole_results = self._run_pothole_detection(
                    temp_path, settings.POTHOLE_CONFIDENCE_THRESHOLD
                )
                yolo_results = self._run_yolo_detection(temp_path)

        finally:
            # Clean up temp file
            os.close(temp_fd)
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        # Build alert string
        alerts = []
        if pothole_results["detected"]:
            alerts.append("⚠️ POTHOLE DETECTED")
        if yolo_results["humans"]["detected"]:
            alerts.append("🧍 HUMAN ON ROAD")
        if yolo_results["vehicles"]["detected"]:
            alerts.append("🚗 VEHICLE NEARBY")
        if yolo_results["animals"]["detected"]:
            alerts.append("🐄 ANIMAL ON ROAD")

        alert_str = " | ".join(alerts) if alerts else "✅ ALL CLEAR"

        return {
            "mode": mode.upper(),
            "pothole": pothole_results,
            "humans": yolo_results["humans"],
            "vehicles": yolo_results["vehicles"],
            "animals": yolo_results["animals"],
            "alert": alert_str,
            "velocity_kmh": velocity_kmh,
        }


# Module-level singleton
_detector: Optional[Detector] = None


def get_detector() -> Detector:
    """Get or create the global Detector singleton."""
    global _detector
    if _detector is None:
        _detector = Detector()
    return _detector