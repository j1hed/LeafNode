from fastapi import APIRouter

from app.services import llm_client, weather_service, youtube_knowledge, websocket_receiver
from app import config

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/llm-status")
def llm_status():
    return llm_client.test_connection()


@router.get("/weather-status")
def weather_status():
    return weather_service.get_current_weather()


@router.get("/websocket-status")
def websocket_status():
    return {
        "running": websocket_receiver._server is not None,
        "host": config.WEBSOCKET_HOST,
        "port": config.WEBSOCKET_PORT,
        "url": f"ws://{config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT}",
        "protocol": "SYNC_REQUEST/DATA",
    }


@router.post("/youtube-fetch/{plant_type}")
def youtube_fetch(plant_type: str, max_videos: int = None):
    return youtube_knowledge.fetch_and_cache_growth_data(plant_type, max_videos=max_videos)