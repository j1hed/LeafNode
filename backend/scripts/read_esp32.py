import requests
import json
import time
import sys
from datetime import datetime
import os

BASE_URL = "http://localhost:8000"


def print_separator(title):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def check_server():
    try:
        r = requests.get(f"{BASE_URL}/api/status", timeout=5)
        if r.status_code == 200:
            print(f"✅ Server is running")
            return True
        else:
            print(f"❌ Server returned status {r.status_code}")
            return False
    except requests.ConnectionError:
        print(f"❌ Cannot connect to server at {BASE_URL}")
        return False


def get_latest_sensor_data():
    try:
        r = requests.get(f"{BASE_URL}/api/sensors/latest", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "ok":
                return data.get("data")
            else:
                return None
        return None
    except:
        return None


def display_sensor_data(data):
    if not data:
        print("No data available")
        return

    print_separator("ESP32 SENSOR DATA")
    print(f"ID:          {data.get('id')}")
    print(f"Temperature: {data.get('temperature')} °C")
    print(f"Humidity:    {data.get('humidity')} %")
    print(f"Pressure:    {data.get('pressure')} hPa")
    print(f"Gas:         {data.get('gas')} kOhm")
    print(f"Light:       {data.get('light')} %")
    print(f"Soil:        {data.get('soil')} %")
    print(f"pH:          {data.get('ph')}")
    print(f"Timestamp:   {data.get('timestamp')}")


def monitor_realtime(interval=3):
    print_separator("REAL-TIME MONITORING")
    print(f"Polling every {interval} seconds")
    print("Press Ctrl+C to stop")
    print()

    last_id = None
    no_data_count = 0

    try:
        while True:
            data = get_latest_sensor_data()

            if data:
                current_id = data.get('id')

                if current_id != last_id:
                    # Clear screen for better visibility
                    clear_screen()
                    print("=" * 60)
                    print("LEAFNODE - REAL-TIME MONITORING")
                    print("=" * 60)

                    # Display with color coding
                    temp = data.get('temperature', 0)
                    soil = data.get('soil', 0)

                    # Temperature indicator
                    if temp > 30:
                        temp_status = "🔴 HIGH"
                    elif temp < 15:
                        temp_status = "🔵 LOW"
                    else:
                        temp_status = "🟢 NORMAL"

                    # Soil moisture indicator
                    if soil < 30:
                        soil_status = "🔴 DRY"
                    elif soil > 70:
                        soil_status = "🔵 WET"
                    else:
                        soil_status = "🟢 OPTIMAL"

                    print(f"\n📊 SENSOR DATA (ID: {current_id})")
                    print("-" * 40)
                    print(f"🌡️  Temperature: {temp:6.2f}°C  [{temp_status}]")
                    print(f"💧 Humidity:    {data.get('humidity', 0):6.2f}%")
                    print(f"🌡️  Pressure:    {data.get('pressure', 0):6.2f} hPa")
                    print(f"💨 Gas:         {data.get('gas', 0):6.2f} kOhm")
                    print(f"💡 Light:       {data.get('light', 0):6d}%")
                    print(f"🌱 Soil:        {soil:6d}%  [{soil_status}]")
                    print(f"🧪 pH:          {data.get('ph', 0):6.2f}")
                    print(f"🕐 Time:        {data.get('timestamp', 'N/A')}")
                    print("-" * 40)

                    last_id = current_id
                    no_data_count = 0
                else:
                    no_data_count += 1
                    print(f"\r⏳ Waiting for new data... (same ID: {current_id}, waiting {no_data_count * interval}s)",
                          end='', flush=True)
            else:
                no_data_count += 1
                print(f"\r⏳ Waiting for ESP32 data... ({no_data_count * interval}s)", end='', flush=True)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")


def monitor_simple(interval=3):
    """Simple monitoring that always displays data"""
    print_separator("SIMPLE MONITORING")
    print(f"Refreshing every {interval} seconds")
    print("Press Ctrl+C to stop")

    try:
        while True:
            clear_screen()
            print("=" * 60)
            print("LEAFNODE - LIVE DATA")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)

            data = get_latest_sensor_data()
            if data:
                print(f"\n📊 ESP32 SENSOR DATA")
                print(f"  ID:          {data.get('id')}")
                print(f"  Temperature: {data.get('temperature')}°C")
                print(f"  Humidity:    {data.get('humidity')}%")
                print(f"  Pressure:    {data.get('pressure')} hPa")
                print(f"  Gas:         {data.get('gas')} kOhm")
                print(f"  Light:       {data.get('light')}%")
                print(f"  Soil:        {data.get('soil')}%")
                print(f"  pH:          {data.get('ph')}")
                print(f"  Last Update: {data.get('timestamp')}")

                # Check if data is stale
                try:
                    last_time = datetime.fromisoformat(data.get('timestamp', ''))
                    now = datetime.now()
                    age = (now - last_time).total_seconds()
                    if age > 10:
                        print(f"\n  ⚠️ WARNING: Data is {age:.0f} seconds old!")
                        print(f"  ESP32 might not be sending data")
                except:
                    pass
            else:
                print("\n⏳ No data from ESP32")
                print("   Check:")
                print("   1. ESP32 is powered on")
                print("   2. ESP32 is connected to WiFi")
                print("   3. ESP32 code is running")

            # Check ESP32 connection status
            try:
                r = requests.get(f"{BASE_URL}/api/status", timeout=5)
                status = r.json()
                print(f"\n\n🖥️  Server: {status.get('status', 'unknown')}")
                print(f"📡 WebSocket: {status.get('websocket_receiver', 'N/A')}")
            except:
                print("\n❌ Server not accessible")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped")


def main():
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "latest":
            data = get_latest_sensor_data()
            display_sensor_data(data)

        elif command == "monitor":
            interval = 3
            if len(sys.argv) > 2:
                try:
                    interval = int(sys.argv[2])
                except ValueError:
                    pass
            monitor_realtime(interval)

        elif command == "simple":
            interval = 3
            if len(sys.argv) > 2:
                try:
                    interval = int(sys.argv[2])
                except ValueError:
                    pass
            monitor_simple(interval)

        else:
            print(f"Unknown command: {command}")
            print_usage()
    else:
        data = get_latest_sensor_data()
        display_sensor_data(data)


def print_usage():
    print("\nUsage:")
    print("  python read_esp32.py latest       # Show latest data once")
    print("  python read_esp32.py monitor [N]  # Show only new data (default 3s)")
    print("  python read_esp32.py simple [N]   # Always refresh display (default 3s)")


if __name__ == "__main__":
    print_separator("LEAFNODE - ESP32 DATA READER")

    if not check_server():
        print("Start server with: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(1)

    main()