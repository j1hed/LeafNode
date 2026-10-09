"""
services/soil_service.py

NOTE: your real-time soil moisture already comes from the ESP32
sensor payload (`soil` field in /api/sensors) - that's the primary
source and it's handled in routers/hardware.py + services/agent.py.

This module is only for the *optional* supplementary RapidAPI
"PlantLink" soil lookup that existed in `API Soil/plantlink.py`. That
original script pointed at a placeholder endpoint ("/your-endpoint"),
so this wrapper is intentionally conservative: it's disabled unless
you configure RAPIDAPI_KEY and returns {"available": False} rather
than pretending to have real data.

Wire in a different provider here later if you settle on one - the
agent only expects available / a dict of fields back.
"""

from app import config


def get_supplementary_soil_data(location: str = None) -> dict:
    if not config.RAPIDAPI_KEY:
        return {"available": False, "reason": "RAPIDAPI_KEY not configured"}

    # Left intentionally unimplemented: the original plantlink.py
    # pointed at "/your-endpoint", which was never a real, working
    # RapidAPI route. Plug in the exact endpoint from your RapidAPI
    # subscription here once you have it, following the same pattern
    # as weather_service.get_current_weather().
    return {"available": False, "reason": "soil provider endpoint not configured yet"}
