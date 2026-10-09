import requests
import json
import time
import sys
from datetime import datetime

BASE = "http://localhost:8000"


def step(title):
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")


def get_latest_sensor():
    """Get the latest REAL sensor data from ESP32"""
    r = requests.get(f"{BASE}/api/sensors/latest", timeout=5)
    data = r.json()
    if data.get("status") == "ok":
        return data.get("data")
    return None


def display_sensor(sensor):
    if not sensor:
        print("❌ No sensor data available")
        return
    print(f"📊 ESP32 Sensor Data (ID: {sensor['id']})")
    print(f"   Temperature: {sensor['temperature']}°C")
    print(f"   Humidity:    {sensor['humidity']}%")
    print(f"   Soil:        {sensor['soil']}%")
    print(f"   Light:       {sensor['light']}%")
    print(f"   pH:          {sensor['ph']}")
    print(f"   Timestamp:   {sensor['timestamp']}")


def main():
    step("1. Getting REAL ESP32 Sensor Data")
    sensor = get_latest_sensor()
    display_sensor(sensor)

    if not sensor:
        print("\n❌ No sensor data! Make sure ESP32 is sending data.")
        print("   Check Serial Monitor for HTTP 200 responses.")
        sys.exit(1)

    # Check if data is fresh (less than 10 seconds old)
    try:
        last_update = datetime.fromisoformat(sensor['timestamp'])
        age = (datetime.now() - last_update).total_seconds()
        if age > 10:
            print(f"\n⚠️ Warning: Data is {age:.0f} seconds old")
            print("   ESP32 might not be sending data")
            response = input("   Continue anyway? (y/n): ")
            if response.lower() != 'y':
                sys.exit(1)
    except:
        pass

    step("2. Checking for Jetson Detection")
    r = requests.get(f"{BASE}/api/detections/latest", timeout=5)
    detection_data = r.json()
    if detection_data.get("status") == "ok":
        detection = detection_data.get("data")
        print(f"🤖 Latest detection: {detection.get('disease')} ({detection.get('confidence')}%)")
        print(f"   Detected at: {detection.get('date')} {detection.get('hour')}")
    else:
        print("⏳ No Jetson detection yet")
        print("   You can still create a session without disease detection")

    step("3. Creating Recommendation Session with REAL Data")
    plant_type = input("Enter plant type (default: tomato): ").strip() or "tomato"

    r = requests.post(f"{BASE}/api/recommendation/sessions",
                      json={"plant_type": plant_type}, timeout=10)

    if r.status_code != 200:
        print(f"❌ Error creating session: {r.json()}")
        sys.exit(1)

    session = r.json()
    session_id = session["id"]
    print(f"✅ Session {session_id} created")
    print(f"   Status: {session['status']}")

    # Show what data was captured
    if session.get('sensor_snapshot'):
        sensor_snap = session['sensor_snapshot']
        if isinstance(sensor_snap, str):
            sensor_snap = json.loads(sensor_snap)
        if sensor_snap:
            print(f"   Sensor captured: {sensor_snap['temperature']}°C, soil {sensor_snap['soil']}%")

    if session.get('detection_snapshot'):
        det_snap = session['detection_snapshot']
        if isinstance(det_snap, str):
            det_snap = json.loads(det_snap)
        if det_snap:
            print(f"   Detection captured: {det_snap['disease']} ({det_snap['confidence']}%)")

    step("4. Generating Recommendation (LLM)")
    print("   Calling LLM...")
    r = requests.post(f"{BASE}/api/recommendation/sessions/{session_id}/generate", timeout=60)
    result = r.json()

    if result['status'] == 'awaiting_approval':
        print("✅ Recommendation generated!")

        rec = result.get('recommendation_json', {})
        if isinstance(rec, str):
            rec = json.loads(rec)

        print(f"\n📋 Summary: {rec.get('summary', 'N/A')}")
        print(f"\n💧 Care Guide: {rec.get('care_guide', 'N/A')}")

        if rec.get('disease_notes'):
            print(f"\n🦠 Disease Notes: {rec['disease_notes']}")

        alerts = rec.get('alerts', [])
        if alerts:
            print(f"\n⚠️ Alerts:")
            for alert in alerts:
                print(f"   - {alert}")

        actions = rec.get('actions', [])
        if actions:
            print(f"\n⚡ Proposed Actions:")
            for action in actions:
                print(f"   - {action['device']} -> {action['action']} ({action.get('duration_minutes', 'N/A')} min)")
                print(f"     Reason: {action.get('reason', 'N/A')}")
        else:
            print("\n⚡ No actions needed")

    elif result['status'] == 'llm_failed':
        print("❌ LLM failed to generate recommendation")
        rec = result.get('recommendation_json', {})
        if isinstance(rec, str):
            rec = json.loads(rec)
        alerts = rec.get('alerts', [])
        for alert in alerts:
            print(f"   - {alert}")
        sys.exit(1)

    step("5. Approval")
    response = input("\nApprove this recommendation? (y/n): ").strip().lower()

    if response == 'y':
        r = requests.post(f"{BASE}/api/recommendation/sessions/{session_id}/approve", timeout=10)
        approval = r.json()
        print(f"✅ Approved!")
        print(f"   Queued commands: {approval['queued_command_ids']}")

        step("6. Pending Commands for ESP32 #2")
        r = requests.get(f"{BASE}/api/commands/pending", timeout=5)
        commands = r.json()
        print(f"📡 Commands waiting for ESP32 #2: {commands['count']}")

        for cmd in commands['commands']:
            print(f"   - {cmd['device']} -> {cmd['action']} ({cmd.get('duration_minutes', 'N/A')} min)")
            print(f"     Reason: {cmd.get('reason', 'N/A')}")
            print(f"     Status: {cmd['status']}")
            print(f"     Created: {cmd['created_at']}")
    else:
        r = requests.post(f"{BASE}/api/recommendation/sessions/{session_id}/reject", timeout=10)
        print("❌ Recommendation rejected")

    step("Complete!")
    print("Check ESP32 #2 to see if it executes the commands")


if __name__ == "__main__":
    main()