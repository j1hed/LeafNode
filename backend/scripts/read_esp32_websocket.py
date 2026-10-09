import asyncio
import json
import websockets
import requests
from datetime import datetime
import sys

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8765"


def print_separator(title):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)


async def monitor_websocket():
    print_separator("ESP32 WEBSOCKET MONITOR")
    print("Connecting to WebSocket...")

    try:
        async with websockets.connect(WS_URL) as ws:
            print("✅ Connected to WebSocket")

            # Send SYNC_REQUEST
            await ws.send(json.dumps({"type": "SYNC_REQUEST"}))
            reply = await ws.recv()
            print(f"SYNC: {reply}")

            # Monitor for incoming data
            while True:
                try:
                    message = await ws.recv()
                    data = json.loads(message)
                    print(f"\n📊 Received: {data}")
                except websockets.ConnectionClosed:
                    print("Connection closed")
                    break
                except Exception as e:
                    print(f"Error: {e}")
                    break
    except Exception as e:
        print(f"❌ WebSocket error: {e}")


async def monitor_http(interval=3):
    print_separator("ESP32 HTTP MONITOR")
    print(f"Polling every {interval} seconds")
    print("Press Ctrl+C to stop")

    last_id = None

    while True:
        try:
            r = requests.get(f"{BASE_URL}/api/sensors/latest", timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "ok":
                    sensor = data.get("data")
                    if sensor and sensor.get("id") != last_id:
                        print(f"\n📊 New data (ID: {sensor['id']}):")
                        print(f"  Temperature: {sensor['temperature']} °C")
                        print(f"  Humidity: {sensor['humidity']} %")
                        print(f"  Soil: {sensor['soil']} %")
                        print(f"  Light: {sensor['light']} %")
                        print(f"  pH: {sensor['ph']}")
                        print(f"  Time: {sensor['timestamp']}")
                        last_id = sensor.get("id")
                else:
                    print("⏳ Waiting for ESP32 data...")
            else:
                print(f"❌ HTTP {r.status_code}")
        except requests.ConnectionError:
            print("❌ Cannot connect to server")
        except Exception as e:
            print(f"Error: {e}")

        await asyncio.sleep(interval)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "ws":
        asyncio.run(monitor_websocket())
    else:
        interval = 3
        if len(sys.argv) > 1:
            try:
                interval = int(sys.argv[1])
            except ValueError:
                pass
        asyncio.run(monitor_http(interval))


if __name__ == "__main__":
    print("Usage:")
    print("  python read_esp32_websocket.py           # HTTP monitoring (3s)")
    print("  python read_esp32_websocket.py 5         # HTTP monitoring (5s)")
    print("  python read_esp32_websocket.py ws        # WebSocket monitoring")
    print()
    main()