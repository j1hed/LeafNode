import asyncio
import json
import logging
from datetime import datetime

import websockets

from app import config
from app.database import get_connection

logger = logging.getLogger("websocket_receiver")

_server = None


def _get_last_entry_time() -> dict:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT date, hour FROM detections ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    if row:
        return {"last_date": row["date"], "last_hour": row["hour"]}
    return {"last_date": "", "last_hour": ""}


def _save_detection(data: dict) -> bool:
    now = datetime.now()

    detection_date = data.get("date") or now.strftime("%Y-%m-%d")
    detection_hour = data.get("hour") or now.strftime("%H:%M:%S")
    disease = data.get("disease", "unknown")
    confidence = float(data.get("confidence", 0.0))
    timestamp = now.isoformat(timespec="seconds")

    print(f"DEBUG: Saving detection: {detection_date} {detection_hour} - {disease} ({confidence}%)")
    print(f"DEBUG: Using database: {config.DB_FILE}")

    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO detections (
                jetson_detection_id, date, hour, disease, confidence, timestamp
            ) VALUES (NULL, ?, ?, ?, ?, ?)
            """,
            (detection_date, detection_hour, disease, confidence, timestamp),
        )
        inserted = cursor.rowcount > 0
        conn.commit()
        print(f"DEBUG: Insert result - rowcount={cursor.rowcount}, inserted={inserted}")

        cursor.execute("SELECT COUNT(*) as count FROM detections")
        count = cursor.fetchone()['count']
        print(f"DEBUG: Total detections after insert: {count}")

    except Exception as e:
        print(f"DEBUG: ERROR saving detection: {e}")
        inserted = False
    finally:
        conn.close()

    if inserted:
        logger.info("Logged websocket detection: %s at %s %s (%.1f%%)",
                    disease, detection_date, detection_hour, confidence)
    else:
        logger.info("Duplicate websocket detection ignored: %s at %s %s",
                    disease, detection_date, detection_hour)

    return inserted


async def handle_client(websocket):
    peer = websocket.remote_address
    logger.info("Jetson Nano connected from %s", peer)
    print(f"DEBUG: Client connected from {peer}")

    try:
        async for message in websocket:
            print(f"DEBUG: Received raw message: {message[:200]}")

            try:
                msg_data = json.loads(message)
            except json.JSONDecodeError as e:
                print(f"DEBUG: Invalid JSON: {e}")
                logger.warning("Received non-JSON message: %s", message[:200])
                continue

            msg_type = msg_data.get("type")
            print(f"DEBUG: Message type: {msg_type}")

            if msg_type == "SYNC_REQUEST":
                reply = _get_last_entry_time()
                await websocket.send(json.dumps(reply))
                print(f"DEBUG: Sent SYNC reply: {reply}")
                logger.info("SYNC_REQUEST from %s -> %s", peer, reply)

            elif msg_type == "DATA":
                print("DEBUG: Processing DATA message")
                result = _save_detection(msg_data)
                print(f"DEBUG: Save result: {result}")

            else:
                print(f"DEBUG: Unknown message type: {msg_type}")
                logger.warning("Unknown message type '%s' from %s", msg_type, peer)

    except websockets.ConnectionClosed:
        logger.info("Jetson Nano disconnected (%s)", peer)
        print(f"DEBUG: Client disconnected: {peer}")
    except Exception as e:
        logger.error("Error handling websocket client %s: %s", peer, e)
        print(f"DEBUG: Error handling client {peer}: {e}")


async def _serve_forever():
    global _server
    _server = await websockets.serve(
        handle_client,
        config.WEBSOCKET_HOST,
        config.WEBSOCKET_PORT,
    )
    logger.info("WebSocket receiver listening on ws://%s:%d",
                config.WEBSOCKET_HOST, config.WEBSOCKET_PORT)
    print(f"DEBUG: WebSocket server started on {config.WEBSOCKET_HOST}:{config.WEBSOCKET_PORT}")
    await _server.wait_closed()


async def start_websocket_server():
    global _server
    if _server is not None:
        logger.info("WebSocket server already running")
        return _server

    task = asyncio.create_task(_serve_forever())
    for _ in range(50):
        if _server is not None:
            break
        await asyncio.sleep(0.02)

    if _server is None:
        task.cancel()
        raise RuntimeError("WebSocket server failed to start")

    return _server


async def stop_websocket_server():
    global _server
    if _server is not None:
        _server.close()
        await _server.wait_closed()
        _server = None
        logger.info("WebSocket receiver stopped")