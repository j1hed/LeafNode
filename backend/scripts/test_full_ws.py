import asyncio
import json
import requests
import websockets
import time
from datetime import datetime

BASE = "http://localhost:8000"
WS_URL = "ws://localhost:8765"


async def send_detection():
    async with websockets.connect(WS_URL) as ws:
        await ws.send(json.dumps({"type": "SYNC_REQUEST"}))
        print(f"SYNC: {await ws.recv()}")

        # Use unique timestamp including seconds
        now = datetime.now()
        detection = {
            "type": "DATA",
            "date": now.strftime("%Y-%m-%d"),
            "hour": now.strftime("%H:%M:%S"),
            "disease": "Early Blight",
            "confidence": 88.0
        }
        await ws.send(json.dumps(detection))
        print(f"Sent: {detection}")
        await asyncio.sleep(1)


async def main():
    print("1. Testing WebSocket...")
    await send_detection()

    print("\n2. Checking detection...")
    r = requests.get(f"{BASE}/api/detections/latest")
    detection_data = r.json()
    print(
        f"Latest detection: {detection_data['data']['date']} {detection_data['data']['hour']} - {detection_data['data']['disease']}")

    print("\n3. Adding sensor data...")
    sensor_payload = {
        "temperature": 31.5,
        "humidity": 45.0,
        "pressure": 1012.3,
        "gas": 120.5,
        "light": 65,
        "soil": 22,
        "ph": 6.4,
    }
    r = requests.post(f"{BASE}/api/sensors", json=sensor_payload)
    print(f"Sensor POST: {r.status_code}")

    print("\n4. Starting session...")
    r = requests.post(f"{BASE}/api/recommendation/sessions", json={"plant_type": "tomato"})
    if r.status_code != 200:
        print(f"Error: {r.json()}")
        return
    session = r.json()
    print(f"Session {session['id']}: {session['status']}")

    print("\n5. Generating recommendation...")
    r = requests.post(f"{BASE}/api/recommendation/sessions/{session['id']}/generate")
    result = r.json()
    print(f"Status: {result['status']}")

    if result['status'] == 'llm_failed':
        rec_json = result.get('recommendation_json', {})
        if isinstance(rec_json, str):
            rec_json = json.loads(rec_json)
        alerts = rec_json.get('alerts', [])
        print(f"LLM Errors: {alerts}")
        return

    if result.get('recommendation_json'):
        rec = result['recommendation_json']
        if isinstance(rec, str):
            rec = json.loads(rec)
        print(f"Summary: {rec.get('summary', '')[:200]}")
        print(f"Actions: {rec.get('actions', [])}")

    print("\n6. Approving...")
    r = requests.post(f"{BASE}/api/recommendation/sessions/{session['id']}/approve")
    if r.status_code != 200:
        print(f"Approve error: {r.json()}")
        return

    approval = r.json()
    print(f"Approval status: {approval['status']}")
    print(f"Queued commands: {approval['queued_command_ids']}")

    print("\n7. Checking pending commands...")
    r = requests.get(f"{BASE}/api/commands/pending")
    commands = r.json()
    print(f"Pending commands: {commands['count']}")
    for cmd in commands['commands']:
        print(f"  - {cmd['device']} -> {cmd['action']} ({cmd['duration_minutes']} min)")


asyncio.run(main())