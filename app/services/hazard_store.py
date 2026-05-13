import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.db_models import HazardReport, RetrainingContribution
from app.services.geo_utils import haversine

logger = logging.getLogger(__name__)

RETRAINING_QUEUE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "retraining_queue"
)


def create_or_update_report(
    db: Session,
    latitude: float,
    longitude: float,
    confidence: float,
    vehicle_type: str,
    thumbnail_base64: Optional[str] = None,
) -> dict:
    """
    Create a new hazard report or update an existing one via deduplication.

    Dedup logic: if a report exists within 5 meters and is less than 30 days old,
    increment its severity_score and update last_seen instead of creating a new record.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    dedup_cutoff = now - timedelta(days=settings.DEDUP_WINDOW_DAYS)

    # Query all reports to check for nearby duplicates
    # In production with PostGIS this would be a spatial query
    existing_reports = db.query(HazardReport).all()

    for report in existing_reports:
        # Ensure last_seen is timezone-aware for comparison
        report_last_seen = report.last_seen
        if report_last_seen.tzinfo is None:
            report_last_seen = report_last_seen.replace(tzinfo=timezone.utc)

        distance = haversine(latitude, longitude, report.latitude, report.longitude)
        if distance <= settings.DEDUP_RADIUS_M and report_last_seen >= dedup_cutoff:
            # Found a nearby report within dedup window — update it
            report.severity_score += 1
            report.last_seen = now
            if thumbnail_base64:
                report.thumbnail_base64 = thumbnail_base64
            db.commit()
            db.refresh(report)

            return {
                "report_id": report.id,
                "latitude": report.latitude,
                "longitude": report.longitude,
                "severity_score": report.severity_score,
                "first_reported": report.first_reported.isoformat(),
                "last_seen": report.last_seen.isoformat(),
                "is_new": False,
            }

    # No nearby report found — create a new one
    new_report = HazardReport(
        id=str(uuid.uuid4()),
        latitude=latitude,
        longitude=longitude,
        severity_score=1,
        confidence=confidence,
        vehicle_type=vehicle_type,
        first_reported=now,
        last_seen=now,
        thumbnail_base64=thumbnail_base64,
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)

    return {
        "report_id": new_report.id,
        "latitude": new_report.latitude,
        "longitude": new_report.longitude,
        "severity_score": new_report.severity_score,
        "first_reported": new_report.first_reported.isoformat(),
        "last_seen": new_report.last_seen.isoformat(),
        "is_new": True,
    }


def query_hazards(
    db: Session,
    lat: float,
    lng: float,
    radius_m: int = 2000,
    min_severity: int = 1,
) -> dict:
    """
    Query hazard reports near a given location.

    Filters by:
    - Distance (Haversine within radius_m)
    - Severity (>= min_severity)
    - Freshness (last_seen within 90 days)

    Returns sorted by distance ascending, limited to 50 results.
    """
    settings = get_settings()

    # Clamp radius to max
    radius_m = min(radius_m, settings.MAX_SEARCH_RADIUS_M)

    expiry_cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.HAZARD_EXPIRY_DAYS
    )

    # Query all reports and filter in Python (SQLite has no spatial index)
    all_reports = db.query(HazardReport).all()

    hazards = []
    for report in all_reports:
        # Check severity
        if report.severity_score < min_severity:
            continue

        # Check freshness
        report_last_seen = report.last_seen
        if report_last_seen.tzinfo is None:
            report_last_seen = report_last_seen.replace(tzinfo=timezone.utc)
        if report_last_seen < expiry_cutoff:
            continue

        # Check distance
        distance = haversine(lat, lng, report.latitude, report.longitude)
        if distance <= radius_m:
            hazards.append(
                {
                    "report_id": report.id,
                    "latitude": report.latitude,
                    "longitude": report.longitude,
                    "severity_score": report.severity_score,
                    "distance_m": round(distance, 2),
                    "last_seen": report.last_seen.isoformat(),
                }
            )

    # Sort by distance ascending
    hazards.sort(key=lambda x: x["distance_m"])

    # Limit to 50 results
    hazards = hazards[:50]

    return {
        "hazards": hazards,
        "count": len(hazards),
        "query": {"lat": lat, "lng": lng, "radius_m": radius_m},
    }


def get_total_reports_count(db: Session) -> int:
    """Get total number of hazard reports in the database."""
    return db.query(HazardReport).count()


def save_false_negative(
    db: Session,
    latitude: float,
    longitude: float,
    image_files: List,
) -> dict:
    """
    Save false-negative images for future retraining.

    Each image is saved to retraining_queue/ with a UUID filename.
    A database record links the images to the lat/lng.
    """
    # Ensure retraining queue directory exists
    os.makedirs(RETRAINING_QUEUE_DIR, exist_ok=True)

    image_paths = []
    for image_file in image_files:
        # Generate UUID filename
        file_id = str(uuid.uuid4())
        # Determine file extension
        filename = image_file.filename or "image.jpg"
        ext = os.path.splitext(filename)[1] or ".jpg"
        dest_path = os.path.join(RETRAINING_QUEUE_DIR, f"{file_id}{ext}")

        # Write image to disk
        contents = image_file.file.read()
        with open(dest_path, "wb") as f:
            f.write(contents)

        image_paths.append(dest_path)

    # Create database record
    contribution = RetrainingContribution(
        id=str(uuid.uuid4()),
        latitude=latitude,
        longitude=longitude,
        image_paths=json.dumps(image_paths),
        created_at=datetime.now(timezone.utc),
    )
    db.add(contribution)
    db.commit()
    db.refresh(contribution)

    return {
        "contribution_id": contribution.id,
        "images_received": len(image_paths),
        "message": "Thank you — this will improve detection for all users",
    }