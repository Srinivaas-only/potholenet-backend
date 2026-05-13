from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


# ---------- Enums ----------

class VehicleType(str, Enum):
    car = "car"
    motorcycle = "motorcycle"
    truck = "truck"
    bicycle = "bicycle"


class DetectionMode(str, Enum):
    reverse = "reverse"
    driving = "driving"


# ---------- Detection Schemas ----------

class PotholeDetail(BaseModel):
    confidence: float
    x: float
    y: float
    width: float
    height: float


class ObjectDetail(BaseModel):
    label: str
    confidence: float


class DetectionCategory(BaseModel):
    detected: bool
    count: int
    details: List


class DetectionResponse(BaseModel):
    pothole: DetectionCategory
    humans: DetectionCategory
    vehicles: DetectionCategory
    animals: DetectionCategory
    alert: str


class DualModeDetectionResponse(BaseModel):
    mode: str  # "REVERSE" or "DRIVING"
    pothole: DetectionCategory
    humans: DetectionCategory
    vehicles: DetectionCategory
    animals: DetectionCategory
    alert: str
    velocity_kmh: Optional[float] = None


# ---------- Report Schemas ----------

class ReportCreate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    confidence: float = Field(..., ge=0, le=100)
    vehicle_type: VehicleType
    speed_kmh: Optional[float] = None
    thumbnail_base64: Optional[str] = None


class ReportResponse(BaseModel):
    report_id: str
    latitude: float
    longitude: float
    severity_score: int
    first_reported: str
    last_seen: str
    is_new: bool


# ---------- Hazard Query Schemas ----------

class HazardItem(BaseModel):
    report_id: str
    latitude: float
    longitude: float
    severity_score: int
    distance_m: float
    last_seen: str


class HazardQuery(BaseModel):
    lat: float
    lng: float
    radius_m: int


class HazardResponse(BaseModel):
    hazards: List[HazardItem]
    count: int
    query: HazardQuery


# ---------- False Negative Schemas ----------

class FalseNegativeResponse(BaseModel):
    contribution_id: str
    images_received: int
    message: str


# ---------- Health Schemas ----------

class ModelsLoaded(BaseModel):
    pothole: bool
    yolov8: bool


class HealthResponse(BaseModel):
    status: str
    models_loaded: ModelsLoaded
    reports_count: int
    uptime_seconds: float


# ---------- Error Schema ----------

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None