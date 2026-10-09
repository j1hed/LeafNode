from datetime import datetime

from fastapi import APIRouter

from app.database import get_connection
from app.models import SensorData, DetectionData

router = APIRouter(tags=["hardware"])

@router.get("/")
def root():
    return {
        "project": "LeafNode + FarmWise Agent",
        "api": "running",
        "version": "3.1.0",
        "message": "Unified FastAPI server is online",
    }


@router.get("/api/status")
def get_status():
    return {
        "status": "online",
        "project": "LeafNode",
        "timestamp": datetime.now().isoformat(),
        "websocket_receiver": "ws://0.0.0.0:8765",
    }


@router.post("/api/sensors")
def receive_sensor_data(data: SensorData):
    timestamp = datetime.now().isoformat(timespec="seconds")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO sensors (
            temperature, humidity, pressure, gas,
            light, soil, ph, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.temperature,
            data.humidity,
            data.pressure,
            data.gas,
            data.light,
            data.soil,
            data.ph,
            timestamp,
        ),
    )

    sensor_id = cursor.lastrowid
    conn.commit()
    conn.close()

    print()
    print("========================================")
    print("DATA RECEIVED FROM ESP32")
    print("========================================")
    print(f"Temperature : {data.temperature} C")
    print(f"Humidity    : {data.humidity} %")
    print(f"Pressure    : {data.pressure} hPa")
    print(f"Gas         : {data.gas} kOhm")
    print(f"Light       : {data.light} %")
    print(f"Soil        : {data.soil} %")
    print(f"pH          : {data.ph}")
    print("========================================")

    return {
        "status": "ok",
        "source": "ESP32",
        "message": "Sensor data received successfully",
        "id": sensor_id,
        "timestamp": timestamp,
    }


@router.get("/api/sensors/latest")
def get_latest_sensor_data():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sensors ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return {"status": "waiting", "message": "No sensor data received from ESP32 yet"}

    return {"status": "ok", "data": dict(row)}


@router.get("/api/sensors/history")
def get_sensor_history(limit: int = 100):
    limit = max(1, min(limit, 1000))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sensors ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    rows.reverse()

    return {"count": len(rows), "data": rows}


@router.post("/api/detections")
def receive_detection(data: DetectionData):
    now = datetime.now()

    detection_date = data.date or now.strftime("%Y-%m-%d")
    detection_hour = data.hour or now.strftime("%H:%M:%S")
    timestamp = now.isoformat(timespec="seconds")

    conn = get_connection()
    cursor = conn.cursor()

    if data.detection_id is not None:
        cursor.execute(
            """
            INSERT OR IGNORE INTO detections (
                jetson_detection_id, date, hour, disease, confidence, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                data.detection_id,
                detection_date,
                detection_hour,
                data.disease,
                data.confidence,
                timestamp,
            ),
        )
    else:
        cursor.execute(
            """
            INSERT OR IGNORE INTO detections (
                jetson_detection_id, date, hour, disease, confidence, timestamp
            )
            VALUES (NULL, ?, ?, ?, ?, ?)
            """,
            (
                detection_date,
                detection_hour,
                data.disease,
                data.confidence,
                timestamp,
            ),
        )

    inserted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    if inserted:
        print()
        print("========================================")
        print("DATA RECEIVED FROM JETSON NANO (HTTP)")
        print("========================================")
        print(f"Jetson ID  : {data.detection_id}")
        print(f"Disease    : {data.disease}")
        print(f"Confidence : {data.confidence} %")
        print(f"Date       : {detection_date}")
        print(f"Hour       : {detection_hour}")
        print("========================================")
    else:
        print(f"Duplicate Jetson detection ignored safely.")

    return {
        "status": "ok",
        "source": "JETSON_HTTP",
        "message": "AI detection stored successfully" if inserted else "Detection already stored",
        "duplicate": not inserted,
        "detection_id": data.detection_id,
    }


@router.get("/api/detections/latest")
def get_latest_detection():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM detections ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return {"status": "waiting", "message": "No detection received from Jetson yet"}

    return {"status": "ok", "data": dict(row), "source": "websocket_or_http"}


@router.get("/api/detections/history")
def get_detection_history(limit: int = 100):
    limit = max(1, min(limit, 1000))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM detections ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    rows.reverse()

    return {"count": len(rows), "data": rows}


@router.get("/api/latest")
def get_all_latest_data():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sensors ORDER BY id DESC LIMIT 1")
    sensor_row = cursor.fetchone()

    cursor.execute("SELECT * FROM detections ORDER BY id DESC LIMIT 1")
    detection_row = cursor.fetchone()

    conn.close()

    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "esp32": dict(sensor_row) if sensor_row else None,
        "jetson": dict(detection_row) if detection_row else None,
    }


@router.get("/api/analysis")
def get_analysis():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sensors ORDER BY id DESC LIMIT 1")
    sensor_row = cursor.fetchone()

    cursor.execute("SELECT * FROM detections ORDER BY id DESC LIMIT 1")
    detection_row = cursor.fetchone()

    conn.close()

    if sensor_row is None:
        return {"status": "waiting", "message": "No ESP32 sensor data available"}

    sensor = dict(sensor_row)
    detection = dict(detection_row) if detection_row else None

    alerts = []
    actions = []

    if sensor["temperature"] >= 30:
        alerts.append("High temperature")
        actions.append("Cooling recommended")

    if sensor["soil"] <= 30:
        alerts.append("Dry soil")
        actions.append("Irrigation recommended")

    if sensor["light"] <= 20:
        alerts.append("Low light level")
        actions.append("Additional lighting may be required")

    if sensor["ph"] < 5.5 or sensor["ph"] > 7.5:
        alerts.append("Abnormal pH")

    if detection is not None:
        disease = detection["disease"]
        confidence = detection["confidence"]

        if disease.lower() != "healthy" and confidence >= 70:
            alerts.append(f"Plant disease detected: {disease}")
            actions.append("Inspect affected plant")

    system_state = "NORMAL" if not alerts else "ATTENTION"

    return {
        "status": "ok",
        "system_state": system_state,
        "alerts": alerts,
        "recommended_actions": actions,
        "sensor_data": sensor,
        "ai_detection": detection,
    }