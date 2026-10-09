import asyncio
import json
import websockets
from datetime import datetime
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from app.config import DB_FILE


async def test():
    print(f"Database: {DB_FILE}")
    print(f"Database exists: {os.path.exists(DB_FILE)}")

    # Check current database content
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM detections")
    count = cursor.fetchone()['count']
    print(f"Current detections: {count}")
    conn.close()

    # Test WebSocket
    print("\nConnecting to WebSocket...")
    try:
        async with websockets.connect("ws://localhost:8765") as ws:
            print("Connected!")

            # Send SYNC
            await ws.send(json.dumps({"type": "SYNC_REQUEST"}))
            reply = await ws.recv()
            print(f"SYNC reply: {reply}")

            # Send DATA with unique disease name
            now = datetime.now()
            unique_disease = f"TEST_{now.strftime('%H%M%S')}"
            detection = {
                "type": "DATA",
                "date": now.strftime("%Y-%m-%d"),
                "hour": now.strftime("%H:%M:%S"),
                "disease": unique_disease,
                "confidence": 99.9
            }
            print(f"\nSending: {detection}")
            await ws.send(json.dumps(detection))

            # Wait
            await asyncio.sleep(2)

            # Check SYNC again
            await ws.send(json.dumps({"type": "SYNC_REQUEST"}))
            reply2 = await ws.recv()
            print(f"SYNC after: {reply2}")

    except Exception as e:
        print(f"WebSocket error: {e}")
        return

    # Check database
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM detections")
    count2 = cursor.fetchone()['count']
    print(f"\nDetections after: {count2} (was {count})")

    if count2 > count:
        cursor.execute("SELECT * FROM detections ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        print(f"Latest: {dict(row)}")
    else:
        print("NO NEW DETECTION SAVED!")
        # Check if there's an error in the table
        cursor.execute("SELECT * FROM detections ORDER BY id DESC LIMIT 5")
        rows = cursor.fetchall()
        print("Last 5 detections:")
        for r in rows:
            print(dict(r))
    conn.close()


asyncio.run(test())