import math


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