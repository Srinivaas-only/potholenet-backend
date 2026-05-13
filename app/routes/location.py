import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import LocationResponse, ErrorResponse
from app.services.geo_utils import get_location_from_ip

logger = logging.getLogger(__name__)

router = APIRouter(tags=["location"])


@router.get(
    "/location",
    response_model=LocationResponse,
    summary="Get the user's approximate location based on IP address",
    responses={
        500: {"model": ErrorResponse, "description": "Geolocation failed"},
    },
)
async def get_user_location(request: Request):
    """
    Automatically detect the user's approximate location from their IP address.

    Uses the ip-api.com free geolocation service. Returns coordinates accurate
    to city-level (~50km). The phone app should use GPS for precise hazard
    detection, but this provides a quick fallback or initial center point.

    **Note:** For local/localhost requests, defaults to Kuala Lumpur, Malaysia.
    """
    # Extract client IP from request
    # Check X-Forwarded-For header first (for reverse proxies / ngrok)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "127.0.0.1"

    try:
        location_data = await get_location_from_ip(client_ip)
        logger.info(f"Location resolved for IP {client_ip}: {location_data.get('city', 'unknown')}")
        return LocationResponse(**location_data)
    except Exception as e:
        logger.error(f"Location lookup failed for IP {client_ip}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Could not determine location: {str(e)}",
        )