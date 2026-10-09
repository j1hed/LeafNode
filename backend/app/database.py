import sqlite3
from app.config import DB_FILE


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            expires_at INTEGER NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS user_sessions_expiry ON user_sessions(expires_at)")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sensors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            pressure REAL NOT NULL,
            gas REAL NOT NULL,
            light INTEGER NOT NULL,
            soil INTEGER NOT NULL,
            ph REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jetson_detection_id INTEGER,
            date TEXT NOT NULL,
            hour TEXT NOT NULL,
            disease TEXT NOT NULL,
            confidence REAL NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS recommendation_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'collecting',
            sensor_snapshot TEXT,
            detection_snapshot TEXT,
            weather_snapshot TEXT,
            disease_context TEXT,
            growth_context TEXT,
            llm_provider TEXT,
            llm_model TEXT,
            recommendation_json TEXT,
            recommendation_text TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            decided_at TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            device TEXT NOT NULL,
            action TEXT NOT NULL,
            duration_minutes REAL,
            reason TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            acked_at TEXT,
            FOREIGN KEY (session_id) REFERENCES recommendation_sessions (id)
        )
        """
    )

    conn.commit()
    conn.close()
    print("SQLite database ready:", DB_FILE)


def migrate_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='detections'")
    schema = cursor.fetchone()

    if schema:
        schema_sql = schema[0]
        needs_migration = False

        if 'UNIQUE(date, hour, disease)' in schema_sql:
            needs_migration = True
            print("Found UNIQUE constraint - will remove")

        if 'jetson_detection_id INTEGER NOT NULL' in schema_sql:
            needs_migration = True
            print("Found NOT NULL on jetson_detection_id - will remove")

        if needs_migration:
            print("Migrating detections table...")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detections_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jetson_detection_id INTEGER,
                    date TEXT NOT NULL,
                    hour TEXT NOT NULL,
                    disease TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)

            cursor.execute("""
                INSERT INTO detections_new (id, jetson_detection_id, date, hour, disease, confidence, timestamp)
                SELECT id, jetson_detection_id, date, hour, disease, confidence, timestamp
                FROM detections
            """)

            cursor.execute("DROP TABLE detections")
            cursor.execute("ALTER TABLE detections_new RENAME TO detections")
            conn.commit()
            print("Migration complete")

    conn.close()
