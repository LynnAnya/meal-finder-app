import logging
import re
from typing import Any
import httpx

logger = logging.getLogger("osm_service")

# Official OpenStreetMap Overpass API Endpoint
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# West End, Brisbane QLD 4101 Coordinates
WEST_END_LAT = -27.4838
WEST_END_LON = 153.0076
SEARCH_RADIUS_METERS = 3000
TARGET_COUNT = 50

# Map OSM day codes to readable abbreviations
OSM_DAY_MAP = {
    "Mo": "Mon",
    "Tu": "Tue",
    "We": "Wed",
    "Th": "Thu",
    "Fr": "Fri",
    "Sa": "Sat",
    "Su": "Sun",
}

# Normalize amenity tags (combines pub and bar)
AMENITY_DISPLAY_MAP = {
    "restaurant": "Restaurant",
    "cafe": "Cafe",
    "fast_food": "Fast Food",
    "pub": "Bar & Pub",
    "bar": "Bar & Pub",
    "food_court": "Food Court",
    "ice_cream": "Dessert & Ice Cream",
}


def _clean_text(raw_val: Any, max_len: int) -> str:
    """Strips unprintable control characters and HTML brackets safely."""
    if not raw_val or not isinstance(raw_val, str):
        return ""
    printable = "".join(ch for ch in raw_val if ch.isprintable())
    cleaned = printable.replace("<", "").replace(">", "").strip()
    return cleaned[:max_len]


def clean_osm_opening_hours(raw_hours: str | None) -> str | None:
    """
    Cleans day abbreviations while keeping original time intervals and 'PH' intact.
    Returns None if missing or blank so the database stores NULL.
    """
    if not raw_hours or not isinstance(raw_hours, str):
        return None

    val = raw_hours.strip()
    if not val:
        return None

    if "24/7" in val:
        return "Everyday 24 Hours"

    cleaned = val
    for osm_code, friendly in OSM_DAY_MAP.items():
        cleaned = re.sub(rf"\b{osm_code}\b", friendly, cleaned)

    # Insert a space after commas for readable output (e.g., 'Mon-Sun,PH' -> 'Mon-Sun, PH')
    cleaned = re.sub(r",([A-Za-z])", r", \1", cleaned)
    return cleaned[:100]


def _format_cuisine(raw_cuisine: str | None) -> str | None:
    """
    Cleans and title-cases cuisine tags (e.g., 'nepalese' -> 'Nepalese',
    'italian;pizza' -> 'Italian, Pizza'). Returns None if tag is absent.
    """
    if not raw_cuisine or not isinstance(raw_cuisine, str):
        return None
    cleaned = raw_cuisine.strip().replace(";", ", ").replace("_", " ")
    return cleaned.title()[:50] if cleaned else None


async def fetch_nearby_osm_restaurants(
    lat: float = WEST_END_LAT,
    lon: float = WEST_END_LON,
    radius: int = SEARCH_RADIUS_METERS,
    target_count: int = TARGET_COUNT,
) -> list[dict[str, Any]]:
    """
    Queries Overpass API for dining/drinking venues around West End 4101,
    skips unnamed nodes, merges pubs and bars into 'Bar & Pub', formats
    compact street addresses (returns None if no address tags), and returns
    cleaned dictionaries with None for missing fields to store as NULL.
    """
    safe_lat = float(lat)
    safe_lon = float(lon)
    safe_radius = int(radius)
    safe_target = int(target_count)

    # Overpass QL targeting food, drink, and dessert amenities while omitting biergartens
    query = f"""
    [out:json][timeout:25];
    node["amenity"~"restaurant|fast_food|cafe|bar|pub|food_court|ice_cream"](around:{safe_radius}, {safe_lat}, {safe_lon});
    out body {safe_target * 3};
    """

    headers = {
        "User-Agent": "MealFinderApp/1.0 (dev@mealfinder.local)",
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OVERPASS_URL,
                data={"data": query},
                headers=headers,
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException:
        logger.error("OSM Overpass API timed out after 30 seconds.")
        return []
    except httpx.HTTPStatusError as exc:
        logger.error(f"OSM Overpass API returned HTTP {exc.response.status_code}")
        return []
    except Exception as exc:
        logger.error(f"Unexpected error querying Overpass API: {exc}")
        return []

    elements = payload.get("elements", [])
    venues: list[dict[str, Any]] = []
    seen_names: set[str] = set()

    for el in elements:
        tags = el.get("tags", {})
        raw_name = tags.get("name")

        # 1. Skip nodes without a real business name
        if not raw_name or not raw_name.strip():
            continue

        clean_name = _clean_text(raw_name, max_len=100)
        norm_key = clean_name.lower()
        if norm_key in seen_names:
            continue
        seen_names.add(norm_key)

        # 2. Build concise, localized address from addr:* tags (None if no address tags)
        housenumber = _clean_text(tags.get("addr:housenumber", ""), 20)
        street = _clean_text(tags.get("addr:street", ""), 80)
        suburb = _clean_text(tags.get("addr:suburb", ""), 50)

        street_line = f"{housenumber} {street}".strip()
        if street_line and suburb:
            address: str | None = f"{street_line}, {suburb}"
        elif street_line:
            address = street_line
        elif suburb:
            address = suburb
        else:
            address = None

        # 3. Categorize amenity (merging pub and bar)
        raw_amenity = tags.get("amenity", "")
        venue_type = AMENITY_DISPLAY_MAP.get(raw_amenity, "Restaurant")

        # 4. Format cuisine and opening hours (return None when not provided)
        cuisine = _format_cuisine(tags.get("cuisine"))
        opening_hours = clean_osm_opening_hours(tags.get("opening_hours"))

        try:
            r_lat = float(el["lat"])
            r_lon = float(el["lon"])
        except (KeyError, ValueError, TypeError):
            continue

        venues.append({
            "name": clean_name,
            "address": address[:255] if address else None,
            "lat": r_lat,
            "lon": r_lon,
            "venue_type": venue_type,
            "cuisine": cuisine,
            "opening_hours": opening_hours,
        })

        if len(venues) >= safe_target:
            break

    return venues