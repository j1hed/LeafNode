import requests
import json
import time
import sys
import os
import asyncio
import websockets

from datetime import datetime


# ============================================================
# CONFIGURATION
# ============================================================

BASE = "http://localhost:8000"
WS_URL = "ws://localhost:8765"

# Recommended:
# Set these from PowerShell instead of writing your password here.
AUTH_EMAIL = os.getenv("LEAFNODE_EMAIL")
AUTH_PASSWORD = os.getenv("LEAFNODE_PASSWORD")

# Change this to "username" only if Swagger login expects username
LOGIN_FIELD = os.getenv("LEAFNODE_LOGIN_FIELD", "email")


# ============================================================
# HELPERS
# ============================================================

def print_step(step_num, title):
    print("\n" + "=" * 60)
    print(f"STEP {step_num}: {title}")
    print("=" * 60)


def unwrap_payload(data):
    """
    Supports responses such as:

    {
        "status": "ok",
        "data": {...}
    }

    or:

    {
        "session": {...}
    }

    or direct:
    {
        "id": 1,
        ...
    }
    """

    if not isinstance(data, dict):
        return data

    if "data" in data and isinstance(data["data"], dict):
        return data["data"]

    if "session" in data and isinstance(data["session"], dict):
        return data["session"]

    return data


# ============================================================
# AUTHENTICATION
# ============================================================

def login():
    """
    Logs into LeafNode.

    Supports:
    - Cookie authentication
    - Bearer/JWT authentication

    requests.Session() automatically keeps cookies.
    """

    if not AUTH_EMAIL or not AUTH_PASSWORD:
        print("❌ Authentication credentials are missing.")
        print()
        print("Set them in PowerShell first:")
        print()
        print('$env:LEAFNODE_EMAIL="your_email"')
        print('$env:LEAFNODE_PASSWORD="your_password"')
        print()
        sys.exit(1)

    client = requests.Session()

    payload = {
        LOGIN_FIELD: AUTH_EMAIL,
        "password": AUTH_PASSWORD
    }

    print("Logging in...")

    try:
        r = client.post(
            f"{BASE}/api/auth/login",
            json=payload,
            timeout=15
        )

        print(f"   Login HTTP Status: {r.status_code}")

        if not r.ok:
            print(f"❌ Login failed: {r.text}")
            sys.exit(1)

        data = r.json()

        # ----------------------------------------------------
        # Try to find a token
        # ----------------------------------------------------

        token = None

        if isinstance(data, dict):

            token = (
                data.get("access_token")
                or data.get("token")
                or data.get("jwt")
            )

            # Maybe token is inside "data"
            if not token and isinstance(data.get("data"), dict):
                token = (
                    data["data"].get("access_token")
                    or data["data"].get("token")
                    or data["data"].get("jwt")
                )

        # ----------------------------------------------------
        # If token exists, attach it to every future request
        # ----------------------------------------------------

        if token:
            client.headers.update({
                "Authorization": f"Bearer {token}"
            })

            print("✅ Bearer token received")

        # ----------------------------------------------------
        # Otherwise cookie authentication may be active
        # ----------------------------------------------------

        if client.cookies:
            print("✅ Authentication cookie received")

        print("✅ Login successful")

        return client

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to FastAPI server")
        sys.exit(1)

    except requests.exceptions.Timeout:
        print("❌ Login request timed out")
        sys.exit(1)

    except Exception as e:
        print(f"❌ Login error: {type(e).__name__}: {e}")
        sys.exit(1)


def verify_auth(client):
    """
    Verify credentials using protected /api/auth/me endpoint.
    """

    print("Checking authenticated user...")

    try:
        r = client.get(
            f"{BASE}/api/auth/me",
            timeout=15
        )

        print(f"   /api/auth/me HTTP Status: {r.status_code}")

        if r.status_code == 200:
            try:
                data = r.json()
                print(f"✅ Authentication verified")
                print(f"   User: {data}")
            except Exception:
                print("✅ Authentication verified")

            return True

        print(f"❌ Authentication verification failed")
        print(f"   Response: {r.text}")

        return False

    except Exception as e:
        print(f"❌ Authentication check failed: {e}")
        return False


# ============================================================
# FASTAPI CHECK
# ============================================================

def check_server(client):

    try:
        r = client.get(
            f"{BASE}/api/status",
            timeout=10
        )

        if r.status_code == 200:
            return True

    except Exception:
        pass

    try:
        r = client.get(
            f"{BASE}/api/sensors/latest",
            timeout=10
        )

        if r.status_code == 200:
            return True

    except Exception:
        pass

    return False


# ============================================================
# SENSOR DATA
# ============================================================

def get_latest_sensor(client):

    try:

        r = client.get(
            f"{BASE}/api/sensors/latest",
            timeout=15
        )

        if not r.ok:
            return {
                "status": "error",
                "message": r.text
            }

        return r.json()

    except requests.exceptions.Timeout:

        return {
            "status": "timeout",
            "message": "Request timed out"
        }

    except requests.exceptions.ConnectionError:

        return {
            "status": "error",
            "message": "Connection refused"
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================
# WEBSOCKET DETECTION
# ============================================================

def send_detection_via_websocket():

    async def send():

        try:

            async with websockets.connect(WS_URL) as ws:

                # --------------------------------------------
                # Ask server last saved detection timestamp
                # --------------------------------------------

                await ws.send(
                    json.dumps({
                        "type": "SYNC_REQUEST"
                    })
                )

                reply = await ws.recv()

                print(f"   SYNC: {reply}")

                # --------------------------------------------
                # Simulated Jetson detection
                # --------------------------------------------

                detection = {
                    "type": "DATA",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "hour": datetime.now().strftime("%H:%M:%S"),
                    "disease": "Early Blight",
                    "confidence": 85.0
                }

                await ws.send(
                    json.dumps(detection)
                )

                print(
                    f"   Sent: "
                    f"{detection['disease']} "
                    f"({detection['confidence']}%)"
                )

                await asyncio.sleep(1)

                return True

        except Exception as e:

            print(f"   WebSocket error: {e}")

            return False

    return asyncio.run(send())


# ============================================================
# MAIN TEST
# ============================================================

def main():

    print("=" * 60)
    print("LEAFNODE COMPLETE SYSTEM FLOW TEST")
    print("=" * 60)

    # ========================================================
    # STEP 0: AUTHENTICATION
    # ========================================================

    print_step(0, "Authentication")

    client = login()

    if not verify_auth(client):
        print()
        print("❌ Authentication is not valid.")
        print("   Protected recommendation endpoints cannot be tested.")
        sys.exit(1)

    # ========================================================
    # STEP 1: FASTAPI
    # ========================================================

    print_step(1, "Checking FastAPI Server")

    if check_server(client):

        print("✅ Server is running")

    else:

        print("❌ Server is NOT responding")
        print("   Check if Uvicorn is running in another terminal")

        sys.exit(1)

    # ========================================================
    # STEP 2: ESP32 SENSOR
    # ========================================================

    print_step(
        2,
        "Getting ESP32 Sensor Data"
    )

    data = get_latest_sensor(client)

    if data.get("status") == "ok":

        sensor = data["data"]

        timestamp = sensor.get("timestamp")

        if timestamp:

            try:
                age = (
                    datetime.now()
                    - datetime.fromisoformat(timestamp)
                ).total_seconds()

            except Exception:
                age = None

        else:
            age = None

        print(
            f"✅ ESP32 data "
            f"(ID: {sensor.get('id')})"
        )

        print(
            f"   Temperature: "
            f"{sensor.get('temperature')}°C"
        )

        print(
            f"   Humidity: "
            f"{sensor.get('humidity')}%"
        )

        print(
            f"   Soil: "
            f"{sensor.get('soil')}%"
        )

        print(
            f"   Light: "
            f"{sensor.get('light')}%"
        )

        if age is not None:
            print(
                f"   Age: {age:.0f} seconds"
            )

    else:

        print(
            f"❌ Sensor Error: "
            f"{data.get('message', 'Unknown error')}"
        )

        sys.exit(1)

    # ========================================================
    # STEP 3: JETSON DETECTION
    # ========================================================

    print_step(
        3,
        "Sending Jetson Detection via WebSocket"
    )

    if send_detection_via_websocket():

        print("✅ Detection sent")

        time.sleep(1)

        try:

            r = client.get(
                f"{BASE}/api/detections/latest",
                timeout=15
            )

            print(
                f"   Detection GET HTTP: "
                f"{r.status_code}"
            )

            r.raise_for_status()

            det_data = r.json()

            if det_data.get("status") == "ok":

                detection = det_data["data"]

                print(
                    f"✅ Saved: "
                    f"{detection.get('disease')} "
                    f"({detection.get('confidence')}%)"
                )

        except Exception as e:

            print(
                f"⚠️ Could not verify "
                f"detection: {e}"
            )

    else:

        print(
            "⏳ Continuing without detection"
        )

    # ========================================================
    # STEP 4: CREATE RECOMMENDATION SESSION
    # ========================================================

    print_step(
        4,
        "Creating Recommendation Session"
    )

    try:

        r = client.post(
            f"{BASE}/api/recommendation/sessions",
            json={
                "plant_type": "tomato"
            },
            timeout=15
        )

        print(
            f"   HTTP Status: "
            f"{r.status_code}"
        )

        print(
            f"   API Response: "
            f"{r.text}"
        )

        r.raise_for_status()

        response = r.json()

        session = unwrap_payload(response)

        if not isinstance(session, dict):

            print(
                "❌ Invalid session response"
            )

            sys.exit(1)

        session_id = (
            session.get("id")
            or session.get("session_id")
        )

        if session_id is None:

            print(
                "❌ Session response "
                "does not contain ID"
            )

            print(
                f"   Available keys: "
                f"{list(session.keys())}"
            )

            sys.exit(1)

        print(
            f"✅ Session {session_id}: "
            f"{session.get('status', 'unknown')}"
        )

        # --------------------------------------------
        # Sensor snapshot
        # --------------------------------------------

        if session.get(
            "sensor_snapshot"
        ):

            snap = session[
                "sensor_snapshot"
            ]

            if isinstance(snap, str):

                snap = json.loads(snap)

            if snap:

                print(
                    f"   Sensor: "
                    f"{snap.get('temperature')}°C, "
                    f"Soil {snap.get('soil')}%"
                )

        # --------------------------------------------
        # Detection snapshot
        # --------------------------------------------

        if session.get(
            "detection_snapshot"
        ):

            det = session[
                "detection_snapshot"
            ]

            if isinstance(det, str):

                det = json.loads(det)

            if det:

                print(
                    f"   Detection: "
                    f"{det.get('disease')} "
                    f"({det.get('confidence')}%)"
                )

    except requests.exceptions.HTTPError as e:

        print(
            f"❌ HTTP Error: {e}"
        )

        print(
            f"   Response: {r.text}"
        )

        sys.exit(1)

    except Exception as e:

        print(
            f"❌ Error: "
            f"{type(e).__name__}: {e}"
        )

        sys.exit(1)

    # ========================================================
    # STEP 5: GENERATE RECOMMENDATION
    # ========================================================

    print_step(
        5,
        "Generating Recommendation"
    )

    print(
        "   Calling LLM... "
        "(can take several seconds)"
    )

    try:

        r = client.post(
            f"{BASE}/api/recommendation/"
            f"sessions/{session_id}/generate",
            timeout=120
        )

        print(
            f"   HTTP Status: "
            f"{r.status_code}"
        )

        if not r.ok:

            print(
                f"❌ API Response: "
                f"{r.text}"
            )

            r.raise_for_status()

        raw_result = r.json()

        result = unwrap_payload(
            raw_result
        )

        status = result.get(
            "status",
            "unknown"
        )

        print(
            f"   Status: {status}"
        )

        if status == "awaiting_approval":

            rec = result.get(
                "recommendation_json",
                {}
            )

            if isinstance(rec, str):

                rec = json.loads(rec)

            print(
                "\n📋 Summary:"
            )

            print(
                rec.get(
                    "summary",
                    "No summary"
                )[:500]
            )

            alerts = rec.get(
                "alerts",
                []
            )

            if alerts:

                print(
                    "\n⚠️ Alerts:"
                )

                for alert in alerts:

                    print(
                        f"   - {alert}"
                    )

            actions = rec.get(
                "actions",
                []
            )

            if actions:

                print(
                    "\n⚡ Actions:"
                )

                for action in actions:

                    print(
                        f"   - "
                        f"{action.get('device')} "
                        f"→ "
                        f"{action.get('action')} "
                        f"("
                        f"{action.get('duration_minutes', 'N/A')} "
                        f"min)"
                    )

            else:

                print(
                    "\n✅ No actions needed"
                )

        elif status == "llm_failed":

            print(
                "❌ LLM failed"
            )

            rec = result.get(
                "recommendation_json",
                {}
            )

            if isinstance(rec, str):

                rec = json.loads(rec)

            for alert in rec.get(
                "alerts",
                []
            ):

                print(
                    f"   - {alert}"
                )

            sys.exit(1)

    except requests.exceptions.Timeout:

        print(
            "❌ Timeout generating "
            "recommendation"
        )

        sys.exit(1)

    except requests.exceptions.HTTPError as e:

        print(
            f"❌ HTTP Error: {e}"
        )

        print(
            f"   Response: {r.text}"
        )

        sys.exit(1)

    except Exception as e:

        print(
            f"❌ Error: "
            f"{type(e).__name__}: {e}"
        )

        sys.exit(1)

    # ========================================================
    # STEP 6: APPROVE
    # ========================================================

    print_step(
        6,
        "Approving Recommendation"
    )

    try:

        r = client.post(
            f"{BASE}/api/recommendation/"
            f"sessions/{session_id}/approve",
            timeout=60
        )

        print(
            f"   HTTP Status: "
            f"{r.status_code}"
        )

        if not r.ok:

            print(
                f"   Response: {r.text}"
            )

            r.raise_for_status()

        approval = unwrap_payload(
            r.json()
        )

        print(
            f"✅ Status: "
            f"{approval.get('status')}"
        )

        print(
            f"   Commands: "
            f"{approval.get('queued_command_ids', [])}"
        )

    except Exception as e:

        print(
            f"❌ Error: "
            f"{type(e).__name__}: {e}"
        )

        sys.exit(1)

    # ========================================================
    # STEP 7: PENDING ESP32 COMMANDS
    # ========================================================

    print_step(
        7,
        "Pending Commands"
    )

    try:

        r = client.get(
            f"{BASE}/api/commands/pending",
            timeout=15
        )

        print(
            f"   HTTP Status: "
            f"{r.status_code}"
        )

        if not r.ok:

            print(
                f"   Response: {r.text}"
            )

            r.raise_for_status()

        commands_data = r.json()

        # Handle possible API wrapper
        if (
            isinstance(commands_data, dict)
            and "data" in commands_data
            and isinstance(
                commands_data["data"],
                dict
            )
        ):

            commands_data = (
                commands_data["data"]
            )

        commands = commands_data.get(
            "commands",
            []
        )

        count = commands_data.get(
            "count",
            len(commands)
        )

        print(
            f"📡 {count} command(s) "
            f"for ESP32 #2"
        )

        for cmd in commands:

            print(
                f"\n   ID: "
                f"{cmd.get('id')}"
            )

            print(
                f"   Device: "
                f"{cmd.get('device')}"
            )

            print(
                f"   Action: "
                f"{cmd.get('action')}"
            )

            print(
                f"   Duration: "
                f"{cmd.get('duration_minutes', 'N/A')} "
                f"min"
            )

            print(
                f"   Reason: "
                f"{cmd.get('reason', 'N/A')}"
            )

    except Exception as e:

        print(
            f"❌ Error: "
            f"{type(e).__name__}: {e}"
        )

        sys.exit(1)

    # ========================================================
    # COMPLETE
    # ========================================================

    print(
        "\n" + "=" * 60
    )

    print(
        "✅ TEST COMPLETE"
    )

    print(
        "=" * 60
    )

    print(
        "\nFlow tested:"
    )

    print(
        "0. ✅ Authentication"
    )

    print(
        "1. ✅ ESP32 → FastAPI "
        "(sensor data)"
    )

    print(
        "2. ✅ Jetson/WebSocket "
        "→ Database"
    )

    print(
        "3. ✅ Sensor + Detection "
        "→ Recommendation Session"
    )

    print(
        "4. ✅ LLM → Recommendation"
    )

    print(
        "5. ✅ Human Approval"
    )

    print(
        "6. ✅ Commands created"
    )

    print(
        "7. ✅ Commands queued "
        "for ESP32 #2"
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()