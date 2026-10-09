"""
services/growth_knowledge.py

Lightweight stand-in for the old "Multilingual Plant Growth
Recommendation System" (data_collector.py + vector_database.py, which
pulled YouTube transcripts + trusted gardening sites and indexed them
with sentence-transformers + FAISS).

Rather than re-scraping on every request (slow, and needs several
heavy ML dependencies), this module just searches whatever text you
already have under PLANT_DATA_DIR - for example, drop in the
`summaries/` folders that already exist under
`FarmWise/youtube scraping/growth_of_<plant>/summaries/` from the old
project, one folder per plant, and they'll be picked up automatically:

    plant_data/
      tomato/
        summary_1.txt
        summary_2.txt
      apple/
        ...

Also reads the raw JSON format produced by the old
`youtube scraping/*/summaries/*_summaries.json` scraper directly
(a {"videos": [{"summary": ..., "growth_factors": {...}}, ...]}
shape) - so if you re-run that scraper for a new plant later, you can
drop the JSON straight into plant_data/<plant>/ with no conversion
step. plant_data/apple, banana, broccoli and onion already ship with
real data pre-converted from that scraper into .txt files.

For any OTHER plant with nothing cached yet, get_growth_context()
automatically calls services/youtube_knowledge.py to search YouTube,
pull transcripts, and summarize them with the LLM on the spot - then
the result is cached to plant_data/<plant>/ so it's instant on every
call after the first. Requires YOUTUBE_API_KEY in .env; if that's not
set, this step is just skipped and the LLM falls back to its own
general knowledge for that plant.

Default mode is a simple keyword-overlap search (no extra
dependencies). If sentence-transformers + faiss-cpu are installed,
it transparently switches to real semantic search - see
requirements-optional.txt.
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict

from app import config
from app.services import youtube_knowledge

logger = logging.getLogger("growth_knowledge")

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
    _SEMANTIC_AVAILABLE = True
except ImportError:
    _SEMANTIC_AVAILABLE = False

_model = None  # lazy-loaded sentence-transformers model


def _plant_dir(plant_name: str) -> Path:
    return config.PLANT_DATA_DIR / plant_name.lower().replace(" ", "_")


def _load_chunks(plant_name: str) -> List[str]:
    plant_dir = _plant_dir(plant_name)
    if not plant_dir.exists():
        return []

    chunks = []

    for path in plant_dir.rglob("*.txt"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if text:
                chunks.append(text)
        except OSError:
            continue

    for path in plant_dir.rglob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, json.JSONDecodeError):
            continue
        # raw youtube-scraper format: {"videos": [{"summary":..., "growth_factors": {...}}, ...]}
        for video in raw.get("videos", []):
            summary = (video.get("summary") or "").strip()
            factors = video.get("growth_factors") or {}
            factor_lines = "\n".join(
                f"- {k}: {v}" for k, v in factors.items() if v and v != "Not specified"
            )
            text = f"{summary}\n\nGrowth factors:\n{factor_lines}".strip()
            if text:
                chunks.append(text)

    return chunks


def _keyword_search(chunks: List[str], query: str, top_k: int) -> List[str]:
    query_terms = set(re.findall(r"\w+", query.lower()))
    scored = []
    for chunk in chunks:
        chunk_terms = set(re.findall(r"\w+", chunk.lower()))
        overlap = len(query_terms & chunk_terms)
        if overlap:
            scored.append((overlap, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]


def _semantic_search(chunks: List[str], query: str, top_k: int) -> List[str]:
    global _model
    if _model is None:
        _model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    embeddings = _model.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    query_vec = _model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
    scores, idxs = index.search(query_vec, min(top_k, len(chunks)))

    return [chunks[i] for i in idxs[0] if i < len(chunks)]


def get_growth_context(plant_type: str, user_environment: Dict = None, top_k: int = 4) -> Dict:
    """
    Returns {"available": bool, "snippets": [...], "mode": "semantic"|"keyword"|"none",
             "source": "cached"|"youtube_live"|"none"}
    """
    chunks = _load_chunks(plant_type)
    source = "cached"

    if not chunks:
        if youtube_knowledge.is_configured():
            logger.info(f"No local growth data for '{plant_type}' - searching YouTube live")
            result = youtube_knowledge.fetch_and_cache_growth_data(plant_type)
            if result.get("ok"):
                chunks = _load_chunks(plant_type)  # re-read what was just cached to disk
                source = "youtube_live"
            else:
                logger.info(f"Live YouTube search found nothing for '{plant_type}': {result.get('reason')}")

    if not chunks:
        reason = (
            f"No local growth data for '{plant_type}' and live YouTube search "
            f"{'found nothing usable' if youtube_knowledge.is_configured() else 'is not configured (set YOUTUBE_API_KEY in .env)'}. "
            f"The LLM will rely on its own general knowledge plus your sensor/weather data."
        )
        return {"available": False, "snippets": [], "mode": "none", "source": "none", "reason": reason}

    query = f"growing conditions care guide {plant_type}"
    if user_environment:
        query += " " + " ".join(str(v) for v in user_environment.values() if v)

    if _SEMANTIC_AVAILABLE:
        try:
            snippets = _semantic_search(chunks, query, top_k)
            mode = "semantic"
        except Exception as e:  # pragma: no cover - defensive
            logger.warning(f"Semantic search failed, falling back to keyword search: {e}")
            snippets = _keyword_search(chunks, query, top_k)
            mode = "keyword"
    else:
        snippets = _keyword_search(chunks, query, top_k)
        mode = "keyword"

    return {"available": bool(snippets), "snippets": snippets, "mode": mode, "source": source}


def search_local_context(plant_type: str, query: str, top_k: int = 3) -> Dict:
    """Read cached knowledge using existing search; never fetch or write caches."""
    if not re.fullmatch(r"[\w-]+(?: [\w-]+)*", plant_type or ""):
        return {"available": False, "snippets": [], "mode": "none", "source": "local"}
    chunks = _load_chunks(plant_type)
    if not chunks:
        return {"available": False, "snippets": [], "mode": "none", "source": "local"}
    top_k = max(1, min(top_k, 4))
    # Reuse a loaded semantic model. Never download a model for a chat request.
    if _SEMANTIC_AVAILABLE and _model is not None:
        try:
            snippets = _semantic_search(chunks, query, top_k)
            mode = "semantic"
        except Exception:
            snippets = _keyword_search(chunks, query, top_k)
            mode = "keyword"
    else:
        snippets = _keyword_search(chunks, query, top_k)
        mode = "keyword"
    return {"available": bool(snippets), "snippets": [s[:1800] for s in snippets],
            "mode": mode, "source": "local", "plant": plant_type}
