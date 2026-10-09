# test_ws_manual.py
import asyncio
import json
import websockets


async def test():
    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as ws:
        # Test SYNC_REQUEST
        await ws.send(json.dumps({"type": "SYNC_REQUEST"}))
        reply = await ws.recv()
        print(f"SYNC reply: {reply}")

        # Test DATA message
        detection = {
            "type": "DATA",
            "date": "2026-08-26",
            "hour": "14:30:00",
            "disease": "Early Blight",
            "confidence": 88.5
        }
        await ws.send(json.dumps(detection))
        print(f"DATA sent: {detection}")

        await asyncio.sleep(1)


asyncio.run(test())# test_ws_manual.py
import asyncio
import json
import websockets

async def test():
    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as ws:
        # Test SYNC_REQUEST
        await ws.send(json.dumps({"type": "SYNC_REQUEST"}))
        reply = await ws.recv()
        print(f"SYNC reply: {reply}")

        # Test DATA message
        detection = {
            "type": "DATA",
            "date": "2026-08-26",
            "hour": "14:30:00",
            "disease": "Early Blight",
            "confidence": 88.5
        }
        await ws.send(json.dumps(detection))
        print(f"DATA sent: {detection}")

        await asyncio.sleep(1)

asyncio.run(test())