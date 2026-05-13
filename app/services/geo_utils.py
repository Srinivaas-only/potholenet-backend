import math
import logging
from typing import Optional, Dict

import httpx

logger = logging.getLogger(__name__)


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculate the Haversine distance between two points on Earth.

    Args:
        lat1, lng1: Latitude and longitude of point 1 (in degrees).
        lat2, lng2: Latitude and longitude of point 2 (in degrees).

    Returns:
        Distance between the two points in meters.
    """
    EARTH_RADIUS_M = 6371000  # Earth's radius in meters

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lng = math.radians(lng2 - lng1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_M * c


async def get_location_from_ip(ip_address: str) -> Dict:
    """
    Get approximate geographic location from an IP address using ip-api.com.

    Args:
        ip_address: The IP address to geolocate.

    Returns:
        Dict with latitude, longitude, city, region, country, etc.

    Raises:
        Exception: If the geolocation API call fails.
    """
    # Skip private/local IPs
    if ip_address in ("127.0.0.1", "localhost", "::1"):
        # Default to Kuala Lumpur for local testing
        return {
            "ip": ip_address,
            "latitude": 3.139,
            "longitude": 101.6869,
            "city": "Kuala Lumpur",
            "region": "Wilayah Persekutuan",
            "country": "Malaysia",
            "accuracy_km": 50.0,
            "source": "ip_geolocation",
        }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"http://ip-api.com/json/{ip_address}?fields=status,message,lat,lon,city,regionName,country,query"
        )
        data = response.json()

        if data.get("status") != "success":
            logger.warning(f"IP geolocation failed for {ip_address}: {data.get('message', 'unknown error')}")
            raise Exception(f"Geolocation failed: {data.get('message', 'unknown error')}")

        return {
            "ip": data.get("query", ip_address),
            "latitude": data["lat"],
            "longitude": data["lon"],
            "city": data.get("city"),
            "region": data.get("regionName"),
            "country": data.get("country"),
            "accuracy_km": 50.0,
            "source": "ip_geolocation",
        }
