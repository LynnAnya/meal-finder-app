import math

def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Calculates Haversine distance in meters."""
    r = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return int(r * c)

def estimate_walk_minutes(distance_meters: int) -> int:
    """Estimates walking minutes at ~80m/min pace."""
    return max(1, round(distance_meters / 80))