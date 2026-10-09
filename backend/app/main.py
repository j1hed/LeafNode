import asyncio
import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.database import init_database, migrate_database
from app.routers import hardware, recommendation, actuators, system, auth, chatbot
from app.services import websocket_receiver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

app = FastAPI(
    title="LeafNode +  Agent",
    description="ESP32/Jetson data ingestion, plant care & disease recommendation agent, "
                "and pump/fan actuator control - all in one API.",
    version="3.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "Authorization"],
)

app.include_router(hardware.router)
app.include_router(auth.router)
app.include_router(recommendation.router, dependencies=[Depends(auth.get_current_user)])
app.include_router(actuators.router)
app.include_router(system.router)
app.include_router(chatbot.router)


@app.on_event("startup")
async def on_startup():
    init_database()
    migrate_database()

    try:
        await websocket_receiver.start_websocket_server()
        logging.info("WebSocket receiver started successfully")
    except Exception as e:
        logging.error(f"Failed to start WebSocket receiver: {e}")


@app.on_event("shutdown")
async def on_shutdown():
    await websocket_receiver.stop_websocket_server()
