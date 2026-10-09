"""
services/youtube_knowledge.py

Live version of the old `youtube scraping/main.py` +
`youtube scraping/summerization.py` pipeline:

  1. search YouTube for videos about growing a given plant
     (YouTube Data API v3 - needs YOUTUBE_API_KEY)
  2. pull each video's transcript (youtube-transcript-api - no key needed)
  3. summarize the transcript + extract the same fixed growth-factor
     keys the original scraper used, via the LLM (LM Studio/Groq)
  4. cache the result to PLANT_DATA_DIR/<plant>/ in the same .txt
     format growth_knowledge.py already reads - so this only runs
     once per plant, not on every request

This is what lets the agent answer for ANY plant, not just the ones
already pre-scraped (apple/banana/broccoli/onion) - growth_knowledge
calls into here automatically when a plant has no local data yet.
"""

import json
import logging
import re

import requests

from app import config
from app.services import llm_client

logger = logging.getLogger("youtube_knowledge")

try:
    from googleapiclient.discovery import build as build_youtube_client
    _YOUTUBE_API_AVAILABLE = True
except ImportError:
    _YOUTUBE_API_AVAILABLE = False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    _TRANSCRIPT_API_AVAILABLE = False


GROWTH_FACTOR_KEYS = [
    "temperature", "humidity", "method_use", "soil_type",
    "light_exposure", "water_requirements", "fertilizer",
    "pH_level", "plant_spacing",
]


class YouTubeKnowledgeError(Exception):
    pass


def is_configured() -> bool:
    return bool(config.YOUTUBE_API_KEY) and _YOUTUBE_API_AVAILABLE and _TRANSCRIPT_API_AVAILABLE


def _search_videos(query: str, max_results: int) -> list:
    youtube = build_youtube_client("youtube", "v3", developerKey=config.YOUTUBE_API_KEY)
    response = youtube.search().list(
        q=query, part="id,snippet", maxResults=max_results, type="video"
    ).execute()

    videos = []
    for item in response.get("items", []):
        video_id = item["id"]["videoId"]
        videos.append({
            "video_id": video_id,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "title": item.get("snippet", {}).get("title", ""),
        })
    return videos


def _fetch_transcript(video_id: str) -> str:
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    transcript = None
    for lang in config.YOUTUBE_TRANSCRIPT_LANGUAGES:
        try:
            transcript = transcript_list.find_transcript([lang.strip()])
            break
        except Exception:
            continue

    if transcript is None:
        # fall back to whatever transcript exists, auto-translated to English if possible
        transcript = next(iter(transcript_list))
        try:
            transcript = transcript.translate("en")
        except Exception:
            pass

    entries = transcript.fetch()
    return " ".join(entry["text"] for entry in entries)


def _summarize_and_extract_factors(transcript_text: str, plant_name: str) -> dict:
    """One LLM call, structured JSON out: {summary, growth_factors}."""
    # Cap transcript length sent to the LLM - long videos can run well
    # past most local models' context window.
    transcript_excerpt = transcript_text[:6000]

    system_prompt = (
        "You summarize gardening/agriculture video transcripts for a farming app. "
        "Reply with a single valid JSON object and nothing else, in exactly this shape:\n"
        "{\n"
        '  "summary": "3-5 sentence plain-language summary of the growing advice in this video",\n'
        '  "growth_factors": {\n'
        + ",\n".join(f'    "{k}": "value or \'Not specified\'"' for k in GROWTH_FACTOR_KEYS) + "\n"
        "  }\n"
        "}"
    )
    user_prompt = f"Plant: {plant_name}\n\nTranscript:\n{transcript_excerpt}"

    try:
        raw = llm_client.chat_completion(system_prompt, user_prompt, json_mode=True)
    except llm_client.LLMError as e:
        logger.warning(f"LLM summarization failed for {plant_name}: {e}")
        return {
            "summary": transcript_excerpt[:500],
            "growth_factors": {k: "Not specified" for k in GROWTH_FACTOR_KEYS},
        }

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.split("\n", 1)[-1] if cleaned.lower().startswith("json") else cleaned

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        data = json.loads(match.group(0)) if match else {}

    summary = data.get("summary", "") or transcript_excerpt[:500]
    raw_factors = data.get("growth_factors", {}) or {}
    growth_factors = {k: raw_factors.get(k, "Not specified") for k in GROWTH_FACTOR_KEYS}

    return {"summary": summary, "growth_factors": growth_factors}


def _plant_dir(plant_name: str):
    d = config.PLANT_DATA_DIR / plant_name.lower().replace(" ", "_")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _save_snippet(plant_name: str, index: int, video: dict, result: dict):
    factor_lines = "\n".join(
        f"- {k}: {v}" for k, v in result["growth_factors"].items() if v and v != "Not specified"
    )
    text = (
        f"Growth info for {plant_name} (source video: {video['video_url']})\n\n"
        f"{result['summary']}\n\n"
        f"Growth factors:\n{factor_lines}\n"
    )
    path = _plant_dir(plant_name) / f"summary_{index}.txt"
    path.write_text(text, encoding="utf-8")
    return str(path)


def fetch_and_cache_growth_data(plant_name: str, max_videos: int = None) -> dict:
    """
    The on-demand pipeline: search -> transcript -> summarize -> cache
    to plant_data/<plant>/. Returns a status dict; never raises -
    callers should treat a failure here as "no growth data available",
    not a hard error (the LLM can still answer from general knowledge).
    """
    if not config.YOUTUBE_API_KEY:
        return {"ok": False, "reason": "YOUTUBE_API_KEY not configured"}
    if not _YOUTUBE_API_AVAILABLE:
        return {"ok": False, "reason": "google-api-python-client not installed"}
    if not _TRANSCRIPT_API_AVAILABLE:
        return {"ok": False, "reason": "youtube-transcript-api not installed"}

    max_videos = max_videos or config.YOUTUBE_MAX_VIDEOS_PER_PLANT
    query = f"how to grow {plant_name} planting care guide"

    try:
        videos = _search_videos(query, max_videos)
    except Exception as e:
        logger.warning(f"YouTube search failed for '{plant_name}': {e}")
        return {"ok": False, "reason": f"YouTube search failed: {e}"}

    if not videos:
        return {"ok": False, "reason": "No YouTube results for this plant"}

    saved_files = []
    errors = []

    for i, video in enumerate(videos, 1):
        try:
            transcript_text = _fetch_transcript(video["video_id"])
            if not transcript_text.strip():
                raise YouTubeKnowledgeError("empty transcript")
        except Exception as e:
            logger.info(f"No usable transcript for {video['video_url']}: {e}")
            errors.append({"video_url": video["video_url"], "error": str(e)})
            continue

        result = _summarize_and_extract_factors(transcript_text, plant_name)
        path = _save_snippet(plant_name, i, video, result)
        saved_files.append(path)

    return {
        "ok": len(saved_files) > 0,
        "plant": plant_name,
        "videos_found": len(videos),
        "snippets_saved": len(saved_files),
        "saved_files": saved_files,
        "skipped": errors,
    }
