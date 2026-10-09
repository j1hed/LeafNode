import json
import logging
from datetime import datetime

from app import config
from app.database import get_connection
from app.services import weather_service, disease_knowledge, growth_knowledge, llm_client

logger = logging.getLogger("agent")


SYSTEM_PROMPT = """You are an agronomy assistant embedded in a greenhouse automation system.
You receive real sensor readings, an optional AI disease detection, live weather, and
reference growing information, and you must produce a short, practical recommendation.

You MUST reply with a single valid JSON object and nothing else, matching exactly this shape:

{
  "summary": "one short paragraph in plain language",
  "care_guide": "concrete care guidance for this plant given the current conditions",
  "disease_notes": "treatment guidance if a disease was reported, else an empty string",
  "alerts": ["short alert strings, empty list if none"],
  "actions": [
    {"device": "pump", "action": "ON", "duration_minutes": 10, "reason": "why"},
    {"device": "fan", "action": "ON", "duration_minutes": null, "reason": "why"},
    {"device": "peltier", "action": "ON", "duration_minutes": null, "reason": "why"}
  ]
}

Rules for "actions":
- "device" must be exactly one of "pump", "fan", "peltier".
- "action" must be exactly "ON" or "OFF".
- pump = irrigation (soil moisture is low).
- fan = general cooling / air circulation (moderately high temperature).
- peltier = strong active cooling, only for genuinely high temperature - it draws
  significantly more power than the fan, so prefer fan alone for mild heat and only add
  peltier when the fan is unlikely to be enough.
- Only include an action if the current sensor data genuinely justifies it.
- If nothing needs to change, return an empty actions list.
- Never invent devices other than pump, fan and peltier.
- Note: ESP32 #2 already runs its own local safety thresholds for these same three
  actuators independently of you (dry soil -> pump, high temp -> fan, very high temp ->
  peltier+fan). Your approved actions are applied as a temporary override on top of that
  logic for the duration you specify, then control reverts to the local thresholds - so it's
  fine to be conservative and let the local safety net handle borderline cases.
"""


def _row_to_dict(row):
    return dict(row) if row else None


def _latest_sensor():
    conn = get_connection()
    row = conn.execute("SELECT * FROM sensors ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return _row_to_dict(row)


def _latest_detection():
    conn = get_connection()
    row = conn.execute("SELECT * FROM detections ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return _row_to_dict(row)


def create_session(plant_type: str) -> int:
    sensor = _latest_sensor()
    detection = _latest_detection()
    weather = weather_service.get_current_weather()

    disease_context = None
    if detection and detection["disease"].lower() != "healthy" and detection["confidence"] >= config.DISEASE_CONFIDENCE_THRESHOLD:
        try:
            disease_context = disease_knowledge.get_disease_context(
                plant_type, detection["disease"], environment=sensor
            )
        except Exception as e:
            logger.warning(f"Disease knowledge lookup failed: {e}")
            disease_context = {"error": str(e)}

    growth_context = growth_knowledge.get_growth_context(plant_type, user_environment=sensor)

    now = datetime.now().isoformat(timespec="seconds")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO recommendation_sessions (
            plant_type, status, sensor_snapshot, detection_snapshot,
            weather_snapshot, disease_context, growth_context,
            created_at, updated_at
        ) VALUES (?, 'context_ready', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            plant_type,
            json.dumps(sensor) if sensor else None,
            json.dumps(detection) if detection else None,
            json.dumps(weather),
            json.dumps(disease_context) if disease_context else None,
            json.dumps(growth_context),
            now,
            now,
        ),
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()

    logger.info(f"Session #{session_id} created for plant_type={plant_type}")
    return session_id


def _build_user_prompt(session: dict) -> str:
    sensor = json.loads(session["sensor_snapshot"]) if session["sensor_snapshot"] else None
    detection = json.loads(session["detection_snapshot"]) if session["detection_snapshot"] else None
    weather = json.loads(session["weather_snapshot"]) if session["weather_snapshot"] else {}
    disease_context = json.loads(session["disease_context"]) if session["disease_context"] else None
    growth_context = json.loads(session["growth_context"]) if session["growth_context"] else {}

    parts = [f"PLANT: {session['plant_type']}"]

    if sensor:
        parts.append(
            "CURRENT SENSOR READINGS (from ESP32):\n"
            f"- Temperature: {sensor['temperature']} C\n"
            f"- Humidity: {sensor['humidity']} %\n"
            f"- Soil moisture: {sensor['soil']} %\n"
            f"- Light: {sensor['light']} %\n"
            f"- pH: {sensor['ph']}\n"
            f"- Pressure: {sensor['pressure']} hPa\n"
            f"- Gas/air quality: {sensor['gas']}"
        )
    else:
        parts.append("CURRENT SENSOR READINGS: none available yet.")

    if weather.get("available"):
        parts.append(
            "LOCAL WEATHER:\n"
            f"- {weather.get('location')}: {weather.get('condition')}, {weather.get('temp_c')} C, "
            f"humidity {weather.get('humidity')}%, wind {weather.get('wind_kph')} kph"
        )

    if detection:
        parts.append(
            "LATEST AI DISEASE DETECTION (from Jetson via WebSocket):\n"
            f"- Disease: {detection['disease']}\n"
            f"- Confidence: {detection['confidence']}%\n"
            f"- Detected: {detection['date']} {detection['hour']}"
        )

    if disease_context and "error" not in disease_context:
        parts.append(
            "REFERENCE DISEASE INFORMATION (scraped from trusted agronomy sources):\n"
            f"- Symptoms: {'; '.join(disease_context.get('symptoms', [])[:4])}\n"
            f"- Treatments: {'; '.join(disease_context.get('treatments', [])[:4])}\n"
            f"- Prevention: {'; '.join(disease_context.get('prevention', [])[:4])}"
        )

    if growth_context.get("available"):
        joined = "\n---\n".join(growth_context["snippets"])
        parts.append(f"REFERENCE GROWTH INFORMATION:\n{joined}")

    parts.append(
        "Using only the information above (plus your general agronomy knowledge where the "
        "data is silent), produce the JSON recommendation described in your system instructions."
    )

    return "\n\n".join(parts)


def generate_recommendation(session_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM recommendation_sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Session {session_id} not found")

    session = dict(row)
    user_prompt = _build_user_prompt(session)

    try:
        raw_reply = llm_client.chat_completion(SYSTEM_PROMPT, user_prompt, json_mode=True)
        parsed = _safe_parse_json(raw_reply)
        status = "awaiting_approval"
    except llm_client.LLMError as e:
        logger.error(f"LLM call failed for session {session_id}: {e}")
        parsed = {
            "summary": f"Could not reach the LLM provider ({config.LLM_PROVIDER}). "
                       f"Showing sensor data only - no automated actions were proposed.",
            "care_guide": "",
            "disease_notes": "",
            "alerts": [f"LLM error: {e}"],
            "actions": [],
        }
        status = "llm_failed"

    provider_info = llm_client.current_provider_info()

    now = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        """
        UPDATE recommendation_sessions
        SET status = ?, llm_provider = ?, llm_model = ?,
            recommendation_json = ?, recommendation_text = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            status,
            provider_info["provider"],
            provider_info["model"],
            json.dumps(parsed),
            parsed.get("summary", ""),
            now,
            session_id,
        ),
    )
    conn.commit()
    conn.close()

    return parsed


def _safe_parse_json(raw_reply: str) -> dict:
    cleaned = raw_reply.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.split("\n", 1)[-1] if cleaned.lower().startswith("json") else cleaned

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM reply was not valid JSON - storing as plain text with no actions")
        return {
            "summary": raw_reply.strip()[:1000],
            "care_guide": "",
            "disease_notes": "",
            "alerts": ["LLM reply could not be parsed as structured JSON - review manually."],
            "actions": [],
        }

    data.setdefault("summary", "")
    data.setdefault("care_guide", "")
    data.setdefault("disease_notes", "")
    data.setdefault("alerts", [])
    data.setdefault("actions", [])
    return data


def approve_session(session_id: int) -> list:
    conn = get_connection()
    row = conn.execute("SELECT * FROM recommendation_sessions WHERE id = ?", (session_id,)).fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"Session {session_id} not found")

    session = dict(row)
    if session["status"] != "awaiting_approval":
        conn.close()
        raise ValueError(f"Session {session_id} is not awaiting approval (status={session['status']})")

    parsed = json.loads(session["recommendation_json"]) if session["recommendation_json"] else {}
    actions = parsed.get("actions", [])

    now = datetime.now().isoformat(timespec="seconds")
    created_commands = []

    for action in actions:
        device = str(action.get("device", "")).lower()
        act = str(action.get("action", "")).upper()

        if device not in config.KNOWN_DEVICES or act not in ("ON", "OFF"):
            logger.warning(f"Skipping invalid action from LLM: {action}")
            continue

        cursor = conn.execute(
            """
            INSERT INTO commands (session_id, device, action, duration_minutes, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?)
            """,
            (session_id, device, act, action.get("duration_minutes"), action.get("reason"), now),
        )
        created_commands.append(cursor.lastrowid)

    conn.execute(
        "UPDATE recommendation_sessions SET status = 'approved', decided_at = ?, updated_at = ? WHERE id = ?",
        (now, now, session_id),
    )
    conn.commit()
    conn.close()

    logger.info(f"Session #{session_id} approved - {len(created_commands)} command(s) queued")
    return created_commands


def reject_session(session_id: int):
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    conn.execute(
        "UPDATE recommendation_sessions SET status = 'rejected', decided_at = ?, updated_at = ? WHERE id = ?",
        (now, now, session_id),
    )
    conn.commit()
    conn.close()
    logger.info(f"Session #{session_id} rejected")


def get_session(session_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM recommendation_sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"Session {session_id} not found")
    return dict(row)


def list_sessions(limit: int = 50) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM recommendation_sessions ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]