"""Plain-language presentation for the read-only assistant's answers."""
import html
import json
import re
from datetime import datetime


def plain_answer(raw: str, max_words: int = 110, max_sentences: int = 4, *, omit_freshness: bool = False) -> str:
    """Remove report/code formatting while preserving short explanatory prose."""
    text = html.unescape(raw).replace("\\*", "*").replace("\\|", "|")
    text = re.sub(r"<think\b[^>]*>.*?</think>", "", text, flags=re.I | re.S)
    text = re.sub(r"```[^\n]*\n.*?```|```.*?```", "", text, flags=re.S)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</?[a-zA-Z][^>]*>", "", text).strip()
    # Some models return a JSON answer despite being asked for prose.
    try:
        decoded = json.loads(text)
    except (ValueError, TypeError):
        decoded = None
    if isinstance(decoded, dict):
        text = next((decoded[key] for key in ("answer", "explanation", "message", "summary")
                     if isinstance(decoded.get(key), str)), "")
    elif isinstance(decoded, (list, str)):
        text = decoded if isinstance(decoded, str) else ""
    # Remove embedded JSON blocks, never expose action payloads in a chat bubble.
    spans = []
    decoder = json.JSONDecoder()
    for match in re.finditer(r"(?m)^[ \t]*[\[{]", text):
        start = match.start() + len(match.group()) - 1
        try:
            value, length = decoder.raw_decode(text[start:])
        except ValueError:
            continue
        if isinstance(value, (dict, list)):
            spans.append((match.start(), start + length))
    for start, end in reversed(spans):
        text = text[:start] + text[end:]
    lines = []
    for line in text.splitlines():
        if line.count("|") >= 2 or re.match(r"^\s*#{1,6}\s", line):
            continue
        if re.fullmatch(r"\s*(?:\*\*|__)[^\d.!?]+(?:\*\*|__)\s*", line):
            continue
        if line.strip() in ("{", "}", "[", "]", "},", "],"):
            continue
        if re.match(r'^\s*"[^"\n]+"\s*:', line):
            continue
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s+", "", line)
        lines.append(line)
    text = "\n".join(lines)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"(?<!\w)\*([^*\n]+)\*(?!\w)", r"\1", text)
    text = re.sub(r"(?<!\w)_([^_\n]+)_(?!\w)", r"\1", text)
    for technical, friendly in {
        "awaiting_approval": "waiting for your approval",
        "sensor_snapshot": "saved sensor readings",
        "detection_snapshot": "saved plant image analysis",
        "weather_snapshot": "saved weather information",
        "recommendation_json": "saved recommendation",
        "RecommendationSession": "saved recommendation",
    }.items():
        text = text.replace(technical, friendly)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [sentence for sentence in sentences
                 if not re.fullmatch(r"(?:how|why)\?", sentence.strip(), re.I)]
    if omit_freshness:
        # The service adds an accurate age note. Preserve sentences containing readings.
        age_only = re.compile(
            r"^(?:the )?(?:latest )?sensor (?:readings|measurements?|data)\s+"
            r"(?:are|is|were)\s+(?:about\s+)?(?:\d+|one|two|three|four|five|several|a)\s+"
            r"(?:minutes?|hours?|days?|weeks?)\s+old\b", re.I)
        sentences = [sentence for sentence in sentences if not age_only.match(sentence)]
    text = " ".join(sentences[:max_sentences]).strip()
    words = text.split()
    if len(words) > max_words:
        shortened = " ".join(words[:max_words])
        boundaries = list(re.finditer(r"[.!?](?=\s|$)", shortened))
        text = shortened[:boundaries[-1].end()] if boundaries else shortened.rstrip(",:;") + "."
    return text


def age_label(seconds: float) -> str:
    if seconds < 60:
        return "less than a minute"
    if seconds < 3600:
        amount, unit = max(1, round(seconds / 60)), "minute"
    elif seconds < 86400:
        amount, unit = max(1, round(seconds / 3600)), "hour"
    else:
        amount, unit = max(1, round(seconds / 86400)), "day"
    return f"about {amount} {unit}{'s' if amount != 1 else ''}"


def friendly_timestamp(value: str) -> str:
    try:
        when = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return "time unavailable"
    date = f"{when.day} {when.strftime('%B')}"
    if when.year != datetime.now().year:
        date += f" {when.year}"
    return f"{date} at {when:%H:%M}"


def freshness_notes(context: dict) -> list[str]:
    notes = []
    sensor = context.get("latest_sensor")
    if sensor and sensor.get("stale"):
        notes.append(f"The sensor readings are {age_label(sensor['age_seconds'])} old and may not match conditions now.")
    elif sensor and sensor.get("age_seconds") is None:
        notes.append("I cannot confirm how recent the sensor readings are.")
    detection = context.get("latest_detection")
    if detection:
        notes.append(f"Last plant detection: {friendly_timestamp(detection.get('timestamp'))}" +
                     (" (older data)." if detection.get("stale") else "."))
    return notes


def fallback_answer(context: dict) -> str:
    """If a reply contained only tables/code, explain stored facts without another LLM call."""
    session = context.get("recommendation_session")
    if isinstance(session, dict):
        recommendation = session.get("recommendation_json")
        summary = recommendation.get("summary") if isinstance(recommendation, dict) else None
        explanation = plain_answer(summary) if isinstance(summary, str) else ""
        text = "The saved recommendation says: " + explanation if explanation else "This recommendation was created using the sensor readings and plant information saved at that time."
        if session.get("status") == "awaiting_approval":
            text += " It is waiting for your approval in Recommendations."
        return text
    return "I could not give a clear explanation from the available data. Please try a more specific question."
