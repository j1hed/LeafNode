
import sys
import time

import requests

BASE = "http://localhost:8000"


def step(title):
    print(f"\n=== {title} ===")


def main():
    step("1. Fake ESP32 sensor POST")
    sensor_payload = {
        "temperature": 31.5,
        "humidity": 45.0,
        "pressure": 1012.3,
        "gas": 120.5,
        "light": 65,
        "soil": 22,   # deliberately dry, to trigger a pump recommendation
        "ph": 6.4,
    }
    r = requests.post(f"{BASE}/api/sensors", json=sensor_payload)
    print(r.status_code, r.json())

    step("2. Fake Jetson detection POST")
    detection_payload = {
        "detection_id": int(time.time()),
        "disease": "Early Blight",
        "confidence": 88.0,
    }
    r = requests.post(f"{BASE}/api/detections", json=detection_payload)
    print(r.status_code, r.json())

    step("3. Start recommendation session")
    r = requests.post(f"{BASE}/api/recommendation/sessions", json={"plant_type": "tomato"})
    r.raise_for_status()
    session = r.json()
    session_id = session["id"]
    print(f"session_id = {session_id}, status = {session['status']}")

    step("4. Generate recommendation (calls the LLM)")
    r = requests.post(f"{BASE}/api/recommendation/sessions/{session_id}/generate")
    r.raise_for_status()
    session = r.json()
    print("status:", session["status"])
    print("recommendation_json:", session.get("recommendation_json"))

    if session["status"] != "awaiting_approval":
        print("\nLLM call did not succeed - check LM Studio / Groq config (scripts/test_llm.py).")
        sys.exit(1)

    step("5. Approve it")
    r = requests.post(f"{BASE}/api/recommendation/sessions/{session_id}/approve")
    r.raise_for_status()
    approval = r.json()
    print("queued_command_ids:", approval["queued_command_ids"])

    step("6. Pending commands (what ESP32 would poll)")
    r = requests.get(f"{BASE}/api/commands/pending")
    print(r.json())

    commands = r.json()["commands"]
    if commands:
        cmd_id = commands[0]["id"]
        step(f"7. Simulate ESP32 acking command {cmd_id}")
        r = requests.post(f"{BASE}/api/commands/{cmd_id}/ack", json={"success": True})
        print(r.json())
    else:
        print("\nNo actions were proposed for this reading - nothing to ack.")


if __name__ == "__main__":
    main()
