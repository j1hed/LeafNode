"""
services/weather_service.py

Cleaned-up version of the old `API Weather/api.weatherapi.py` snippet:
same WeatherAPI.com endpoint, but the key/location now come from
.env instead of being hardcoded, and it degrades gracefully instead
of crashing when the key is missing or the request fails.
"""

import logging
import requests

from app import config

logger = logging.getLogger("weather_service")


def get_current_weather(location: str = None) -> dict:
    """
    Returns a small dict with the fields the recommendation agent
    actually needs. Returns {"available": False, ...} instead of
    raising, so a missing/invalid API key never breaks a
    recommendation - it just means the agent works from sensor data
    only.
    """
    if not config.WEATHERAPI_KEY:
        return {"available": False, "reason": "WEATHERAPI_KEY not configured"}

    location = location or config.WEATHERAPI_LOCATION
    url = "http://api.weatherapi.com/v1/current.json"
    params = {"key": config.WEATHERAPI_KEY, "q": location, "aqi": "no"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        loc = data.get("location", {})

        return {
            "available": True,
            "location": loc.get("name"),
            "region": loc.get("region"),
            "country": loc.get("country"),
            "local_time": loc.get("localtime"),
            "temp_c": current.get("temp_c"),
            "condition": current.get("condition", {}).get("text"),
            "humidity": current.get("humidity"),
            "wind_kph": current.get("wind_kph"),
            "feelslike_c": current.get("feelslike_c"),
        }
    except requests.RequestException as e:
        logger.warning(f"Weather API request failed: {e}")
        return {"available": False, "reason": str(e)}
