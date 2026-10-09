import requests
import socket
import sys
import json


def test_local_server():
    print("=" * 50)
    print("TESTING LOCAL SERVER CONNECTION")
    print("=" * 50)

    try:
        r = requests.get("http://localhost:8000/api/status", timeout=5)
        print(f"✅ Local server: OK (status {r.status_code})")
        return True
    except requests.ConnectionError:
        print("❌ Local server: NOT RUNNING")
        print("   Start with: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        return False


def test_network_server(ip="192.168.100.128"):
    print(f"\nTesting network server at {ip}...")

    try:
        r = requests.get(f"http://{ip}:8000/api/status", timeout=5)
        print(f"✅ Network server: OK (status {r.status_code})")
        return True
    except requests.ConnectionError:
        print(f"❌ Network server: NOT ACCESSIBLE at {ip}")
        print("   Check:")
        print("   1. Server is running with --host 0.0.0.0")
        print("   2. Windows Firewall allows port 8000")
        print("   3. PC and ESP32 on same network")
        return False
    except requests.Timeout:
        print(f"❌ Timeout connecting to {ip}")
        return False


def test_sensor_endpoint():
    print("\nTesting sensor endpoint...")

    try:
        r = requests.get("http://localhost:8000/api/sensors/latest", timeout=5)
        data = r.json()
        if data.get("status") == "ok":
            print(f"✅ Sensor data available:")
            print(json.dumps(data.get("data"), indent=2))
            return True
        else:
            print(f"⏳ {data.get('message', 'No data')}")
            print("   ESP32 may not be sending data yet")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_firewall():
    print("\nFirewall check:")
    print("Run these commands as Administrator to allow ports:")
    print("  netsh advfirewall firewall add rule name=\"FastAPI 8000\" dir=in action=allow protocol=TCP localport=8000")
    print(
        "  netsh advfirewall firewall add rule name=\"WebSocket 8765\" dir=in action=allow protocol=TCP localport=8765")


def main():
    print("LEAFNODE - ESP32 CONNECTION TEST")
    print()

    local_ok = test_local_server()

    if local_ok:
        test_network_server()
        test_sensor_endpoint()
        test_firewall()

    print("\n" + "=" * 50)
    print("TEST COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()