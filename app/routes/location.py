import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from app import main as app_main
from app.models.schemas import (
    ErrorResponse,
    GPSUpdateRequest,
    GPSUpdateResponse,
    LocationResponse,
    ReverseGeocodeResponse,
)
from app.services.geo_utils import (
    get_location_from_ip,
    reverse_geocode,
    update_gps_state,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["location"])


# ---------------------------------------------------------------------------
# 1. POST /location/update  — Phone pushes GPS coordinates + speed
# ---------------------------------------------------------------------------
@router.post(
    "/location/update",
    response_model=GPSUpdateResponse,
    summary="Upload GPS position and speed from the phone",
    responses={400: {"model": ErrorResponse}},
)
async def push_gps_location(data: GPSUpdateRequest):
    """
    The phone app should call this every 1–2 seconds with its latest GPS fix.

    Stores the position in memory for:
    - `/location/current` — best available location
    - `/location/current-speed` — speed for detection mode
    - `/detect/dual-mode` — auto-selects REVERSE vs DRIVING mode

    Accepts JSON body with latitude, longitude, accuracy, speed, bearing, altitude.
    """
    try:
        # Update the geo_utils GPS state (used by /location/current)
        update_gps_state(
            latitude=data.latitude,
            longitude=data.longitude,
            accuracy_m=data.accuracy_m,
            speed_kmh=data.speed_kmh,
            bearing=data.bearing,
            altitude=data.altitude,
        )

        # Also sync with app_main.gps_state (used by detect.py for mode selection)
        app_main.gps_state["latitude"] = data.latitude
        app_main.gps_state["longitude"] = data.longitude
        app_main.gps_state["velocity_kmh"] = data.speed_kmh
        app_main.gps_state["accuracy_m"] = data.accuracy_m
        app_main.gps_state["last_update"] = time.time()

        logger.info(
            f"GPS updated: ({data.latitude}, {data.longitude}) "
            f"accuracy={data.accuracy_m}m speed={data.speed_kmh}km/h"
        )
        return GPSUpdateResponse(
            status="ok",
            accuracy_m=data.accuracy_m,
            source="phone_gps",
        )
    except Exception as e:
        logger.error(f"GPS update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 2. GET /location/current  — Best available location (GPS > IP fallback)
# ---------------------------------------------------------------------------
@router.get(
    "/location/current",
    response_model=LocationResponse,
    summary="Get best available location (GPS if fresh, else IP)",
    responses={500: {"model": ErrorResponse}},
)
async def get_current_location(request: Request):
    """
    Returns the most accurate location available:

    1. If the phone has pushed GPS data in the last 30 seconds → use that
       (typically 3–5 m accuracy outdoors).
    2. Otherwise → fall back to IP-based geolocation (~50 km accuracy).

    The ESP32-CAM and phone app both call this to find out where they are.
    """
    # Try app_main.gps_state first (synced by /location/update)
    gps = app_main.gps_state
    if gps.get("latitude") is not None and gps.get("last_update") is not None:
        age = time.time() - gps["last_update"]
        if age <= 30:
            accuracy_m = gps.get("accuracy_m", 10.0) or 10.0
            logger.info(f"Returning GPS location: ({gps['latitude']}, {gps['longitude']}) age={age:.1f}s")
            return LocationResponse(
                latitude=gps["latitude"],
                longitude=gps["longitude"],
                accuracy_km=round(accuracy_m / 1000.0, 4),
                source="phone_gps",
            )

    # Fallback to IP geolocation
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    try:
        location_data = await get_location_from_ip(client_ip)
        logger.info(f"Returning IP location for {client_ip}: {location_data.get('city')}")
        return LocationResponse(**location_data)
    except Exception as e:
        logger.error(f"Location lookup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Could not determine location: {e}")


# ---------------------------------------------------------------------------
# 3. GET /location/ip  — IP-only geolocation (always available)
# ---------------------------------------------------------------------------
@router.get(
    "/location/ip",
    response_model=LocationResponse,
    summary="Get approximate location from IP address",
    responses={500: {"model": ErrorResponse}},
)
async def get_ip_location(request: Request):
    """
    Always uses IP geolocation regardless of GPS state.
    Useful as an explicit fallback or for initial map centering.
    Accuracy is city-level (~50 km).

    For local/localhost requests, defaults to Kuala Lumpur, Malaysia.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    try:
        location_data = await get_location_from_ip(client_ip)
        logger.info(f"IP location for {client_ip}: {location_data.get('city')}")
        return LocationResponse(**location_data)
    except Exception as e:
        logger.error(f"IP geolocation failed for {client_ip}: {e}")
        raise HTTPException(status_code=500, detail=f"Could not determine location: {e}")


# ---------------------------------------------------------------------------
# 4. GET /location/current-speed  — Latest GPS speed for detection mode
# ---------------------------------------------------------------------------
@router.get(
    "/location/current-speed",
    summary="Get the latest phone GPS speed and location",
)
async def get_current_speed():
    """
    Get the latest phone GPS speed and location.

    Used by ESP32-CAM and /detect/dual-mode to determine detection mode:
    - velocity_kmh <= 10 → REVERSE mode (YOLO only)
    - velocity_kmh > 10 → DRIVING mode (Pothole + YOLO)
    """
    return {
        "velocity_kmh": app_main.gps_state.get("velocity_kmh"),
        "latitude": app_main.gps_state.get("latitude"),
        "longitude": app_main.gps_state.get("longitude"),
        "last_update": app_main.gps_state.get("last_update"),
    }


# ---------------------------------------------------------------------------
# 5. GET /location/reverse-geocode  — Convert lat/lng → address
# ---------------------------------------------------------------------------
@router.get(
    "/location/reverse-geocode",
    response_model=ReverseGeocodeResponse,
    summary="Convert coordinates to a human-readable address",
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
async def reverse_geocode_location(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
):
    """
    Convert a lat/lng pair into a street address using OpenStreetMap Nominatim.

    Returns address components: road, city, state, country, postal code.
    Free, no API key required.
    """
    try:
        result = await reverse_geocode(lat, lng)
        logger.info(f"Reverse geocode ({lat}, {lng}): {result.get('road', 'unknown')}")
        return ReverseGeocodeResponse(**result)
    except Exception as e:
        logger.error(f"Reverse geocode failed for ({lat}, {lng}): {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Reverse geocode failed: {e}",
        )