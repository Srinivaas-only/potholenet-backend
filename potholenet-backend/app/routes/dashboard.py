import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import main as app_main
from app.database import get_db
from app.models.db_models import HazardReport, PotholeDetection, RetrainingContribution
from app.services.detector import get_detector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])

START_TIME = time.time()


@router.get("/dashboard", response_class=HTMLResponse, summary="Web dashboard UI")
async def dashboard_page():
    """Serve the PotholeNet dashboard HTML page."""
    import os
    html_path = os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@router.get("/api/dashboard/stats", summary="Aggregated dashboard statistics")
async def dashboard_stats(db: Session = Depends(get_db)):
    """Return aggregated stats for the dashboard."""
    try:
        # Counts
        total_reports = db.query(func.count(HazardReport.id)).scalar() or 0
        total_detections = db.query(func.count(PotholeDetection.id)).scalar() or 0
        total_retraining = db.query(func.count(RetrainingContribution.id)).scalar() or 0

        # Average confidence
        avg_confidence = db.query(func.avg(PotholeDetection.confidence)).filter(
            PotholeDetection.confidence > 0
        ).scalar() or 0

        # Severity distribution
        severity_dist = {}
        rows = db.query(HazardReport.severity_score, func.count(HazardReport.id)).group_by(
            HazardReport.severity_score
        ).all()
        for sev, cnt in rows:
            severity_dist[str(sev)] = cnt

        # Recent detections (last 24h, grouped by hour)
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        detections_timeline = []
        det_rows = db.query(
            func.strftime("%Y-%m-%d %H:00", PotholeDetection.detected_at).label("hour"),
            func.count(PotholeDetection.id).label("count")
        ).filter(
            PotholeDetection.detected_at >= since
        ).group_by("hour").all()
        for hour, cnt in det_rows:
            detections_timeline.append({"hour": hour, "count": cnt})

        # Mode distribution
        mode_dist = {}
        mode_rows = db.query(PotholeDetection.mode, func.count(PotholeDetection.id)).group_by(
            PotholeDetection.mode
        ).all()
        for mode, cnt in mode_rows:
            mode_dist[mode] = cnt

        # Recent reports for map (last 100)
        reports = db.query(HazardReport).order_by(
            HazardReport.last_seen.desc()
        ).limit(100).all()

        reports_data = []
        for r in reports:
            reports_data.append({
                "id": r.id,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "severity_score": r.severity_score,
                "confidence": r.confidence,
                "vehicle_type": r.vehicle_type,
                "first_reported": r.first_reported.isoformat() if r.first_reported else None,
                "last_seen": r.last_seen.isoformat() if r.last_seen else None,
            })

        # Recent detections for map (last 100)
        detections = db.query(PotholeDetection).order_by(
            PotholeDetection.detected_at.desc()
        ).limit(100).all()

        detections_data = []
        for d in detections:
            if d.latitude and d.longitude:
                detections_data.append({
                    "id": d.id,
                    "latitude": d.latitude,
                    "longitude": d.longitude,
                    "confidence": d.confidence,
                    "velocity_kmh": d.velocity_kmh,
                    "mode": d.mode,
                    "detected_at": d.detected_at.isoformat() if d.detected_at else None,
                    "pothole_count": d.pothole_count,
                })

        # GPS state
        gps = app_main.gps_state
        gps_age = None
        if gps.get("last_update"):
            gps_age = time.time() - gps["last_update"]

        # Model status
        detector = get_detector()

        return {
            "counts": {
                "total_reports": total_reports,
                "total_detections": total_detections,
                "total_retraining": total_retraining,
            },
            "avg_confidence": round(avg_confidence, 2),
            "severity_distribution": severity_dist,
            "detections_timeline": detections_timeline,
            "mode_distribution": mode_dist,
            "reports": reports_data,
            "detections": detections_data,
            "gps_state": {
                "latitude": gps.get("latitude"),
                "longitude": gps.get("longitude"),
                "velocity_kmh": gps.get("velocity_kmh"),
                "age_seconds": round(gps_age, 1) if gps_age else None,
            },
            "models_loaded": detector.models_loaded,
            "uptime_seconds": round(time.time() - START_TIME, 1),
        }
    except Exception as e:
        logger.error(f"Dashboard stats error: {e}", exc_info=True)
        return {"error": str(e)}