from datetime import datetime
import sqlite3

DB_FILE = "plant_detections.db"


DISEASE = "Early Blight"
CONFIDENCE = 94.7


def ensure_database():
    conn = sqlite3.connect(DB_FILE)
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

    conn.commit()
    conn.close()


def add_test_detection():
    ensure_database()

    now = datetime.now()

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO detections (date, hour, disease, confidence)
        VALUES (?, ?, ?, ?)
        """,
        (
            now.strftime("%Y-%m-%d"),
            now.strftime("%H:%M:%S"),
            DISEASE,
            CONFIDENCE,
        ),
    )

    detection_id = cursor.lastrowid

    conn.commit()
    conn.close()

    print(
        f"Test detection inserted: "
        f"#{detection_id} | {DISEASE} | {CONFIDENCE}%"
    )


if __name__ == "__main__":
    add_test_detection()
