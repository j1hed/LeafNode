
DB_FILE = "plant_detections.db"


PC_IP = "172.20.10.2"
PC_PORT = 8000

API_URL = f"http://{PC_IP}:{PC_PORT}/api/detections"

SYNC_INTERVAL_SECONDS = 2
HTTP_TIMEOUT_SECONDS = 5

def get_connection():
    return sqlite3.connect(DB_FILE)


def init_database():
    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            hour TEXT,
            disease TEXT,
            confidence REAL
        )
        """
    )

    cursor.execute("PRAGMA table_info(detections)")
    columns = [row[1] for row in cursor.fetchall()]

    if "synced" not in columns:
        cursor.execute(
            "ALTER TABLE detections ADD COLUMN synced INTEGER NOT NULL DEFAULT 0"
        )
        print("Added 'synced' column to existing Jetson database.")

    conn.commit()
    conn.close()

    print(f"Jetson database ready: {DB_FILE}")


def get_pending_detections():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, date, hour, disease, confidence
        FROM detections
        WHERE synced = 0
        ORDER BY id ASC
        """
    )

    rows = cursor.fetchall()
    conn.close()

    return rows


def mark_as_synced(detection_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE detections
        SET synced = 1
        WHERE id = ?
        """,
        (detection_id,),
    )

    conn.commit()
    conn.close()


def send_detection(row):
    detection_id, date, hour, disease, confidence = row

    payload = {
        "detection_id": detection_id,
        "date": date,
        "hour": hour,
        "disease": disease,
        "confidence": float(confidence),
    }

    try:
        response = requests.post(
            API_URL,
            json=payload,
            timeout=HTTP_TIMEOUT_SECONDS,
        )

        response.raise_for_status()

        result = response.json()

        if result.get("status") == "ok":
            mark_as_synced(detection_id)

            if result.get("duplicate"):
                print(
                    f"Detection #{detection_id} already exists on PC -> marked synced."
                )
            else:
                print(
                    f"Sent #{detection_id}: "
                    f"{disease} | {float(confidence):.2f}% | "
                    f"{date} {hour}"
                )

            return True

        print(
            f"PC returned unexpected response for #{detection_id}: {result}"
        )
        return False

    except requests.RequestException as error:
        print(
            f"PC unavailable. Detection #{detection_id} stays queued. "
            f"Reason: {error}"
        )
        return False

    except ValueError:
        print(
            f"PC returned invalid JSON for detection #{detection_id}."
        )
        return False


def synchronize():
    rows = get_pending_detections()

    if not rows:
        return

    print(f"{len(rows)} detection(s) waiting for synchronization.")

    for row in rows:
        if not send_detection(row):
            break


def main():
    print("======================================")
    print("LeafNode - Jetson Nano TX")
    print("======================================")
    print(f"FastAPI destination: {API_URL}")

    init_database()

    while True:
        synchronize()
        time.sleep(SYNC_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nJetson TX stopped.")
