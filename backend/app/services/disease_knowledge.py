"""
services/disease_knowledge.py

Ported and trimmed from FarmWise's `Plant Disease Recommandation2 /
plant_disease_agent.py` (PlantDiseaseAgent class). Same idea:

  1. search for the disease across a list of trusted agronomy domains
  2. fetch + parse the pages
  3. regex-extract symptoms / causes / treatments / prevention
  4. cache results per plant+disease under DISEASE_CACHE_DIR so we
     don't re-scrape every time the same disease is asked about

This only runs when the Jetson has actually reported a non-healthy
detection above the confidence threshold - it's context for the LLM
prompt, not a replacement for it.

Also ports the "CAG" (contextual relevance) idea from
`plant_recommendation_system.py`'s CAGProcessor: instead of just
capping each section at N sentences in scrape order, sentences are
ranked by TF-IDF cosine similarity against the plant + current
sensor conditions, so the sentences that actually matter for *this*
plant/environment surface first. Falls back to simple capping if
scikit-learn isn't installed.
"""

import json
import logging
import os
import re
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app import config

logger = logging.getLogger("disease_knowledge")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

CONTENT_SELECTORS = [
    "article", "main", ".content", "#content", ".main-content", ".article",
    ".post-content", ".entry-content", ".page-content", "#main-content",
    ".article-body", ".article-content",
]

SECTION_PATTERNS = {
    "symptoms": [
        r"(?:Symptoms|Signs)[:\s]+(.*?)(?=\b(?:Causes|Treatment|Prevention|Control|Management)\b|$)",
    ],
    "causes": [
        r"(?:Causes|Pathogen|Causal agent)[:\s]+(.*?)(?=\b(?:Symptoms|Treatment|Prevention|Control|Management)\b|$)",
    ],
    "treatments": [
        r"(?:Treatment|Control|Management)[:\s]+(.*?)(?=\b(?:Symptoms|Causes|Prevention)\b|$)",
    ],
    "prevention": [
        r"(?:Prevention|Preventing)[:\s]+(.*?)(?=\b(?:Symptoms|Causes|Treatment|Control|Management)\b|$)",
    ],
}


def _is_trusted(url: str) -> bool:
    domain = urlparse(url).netloc
    return any(trusted in domain for trusted in config.TRUSTED_DISEASE_DOMAINS)


def _search(query: str, num_results: int = 10):
    """
    Use googlesearch-python if it's installed; otherwise fall back to
    a handful of predictable extension-site search URLs so the system
    still returns *something* useful without an extra dependency.
    """
    try:
        from googlesearch import search
        return list(search(query, num_results=num_results))
    except ImportError:
        logger.info("googlesearch-python not installed - using direct extension-site fallback URLs")
        plant_guess = query.split()[0].lower()
        return [
            f"https://extension.umn.edu/plant-diseases/{plant_guess}-diseases",
            f"https://extension.psu.edu/{plant_guess}-diseases",
            f"https://www.gardeningknowhow.com/plant-problems/{plant_guess}-diseases",
        ]


def _clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\S+@\S+\.\S+", "", text)
    text = re.sub(r"http[s]?://\S+", "", text)
    return text


def _extract_content(soup: BeautifulSoup) -> str:
    for selector in CONTENT_SELECTORS:
        node = soup.select_one(selector)
        if node:
            paragraphs = node.find_all("p")
            text = " ".join(p.get_text() for p in paragraphs) if paragraphs else node.get_text()
            return _clean_text(text)

    paragraphs = soup.find_all("p")
    return _clean_text(" ".join(p.get_text() for p in paragraphs))


def _extract_sections(content: str) -> dict:
    result = {"symptoms": [], "causes": [], "treatments": [], "prevention": []}
    for key, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", match)
                result[key].extend(s.strip() for s in sentences if s.strip())
    for key in result:
        result[key] = list(dict.fromkeys(result[key]))[:6]  # dedupe, cap length
    return result


def _rank_by_relevance(sentences: list, query_context: str, top_k: int) -> list:
    """CAG-style relevance ranking: TF-IDF cosine similarity against
    the plant + current sensor context, instead of first-N-found."""
    sentences = list(dict.fromkeys(s for s in sentences if s.strip()))
    if len(sentences) <= top_k:
        return sentences

    if not _SKLEARN_AVAILABLE:
        return sentences[:top_k]

    try:
        corpus = sentences + [query_context]
        vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=2000)
        matrix = vectorizer.fit_transform(corpus)
        query_vec = matrix[-1]
        sims = cosine_similarity(matrix[:-1], query_vec).flatten()
        ranked = [s for _, s in sorted(zip(sims, sentences), key=lambda x: x[0], reverse=True)]
        return ranked[:top_k]
    except ValueError:
        # e.g. empty vocabulary after stop-word removal on very short input
        return sentences[:top_k]


def _cache_path(plant_name: str, disease_name: str) -> str:
    plant_dir = os.path.join(str(config.DISEASE_CACHE_DIR), plant_name.lower().replace(" ", "_"))
    os.makedirs(plant_dir, exist_ok=True)
    return os.path.join(plant_dir, f"{disease_name.lower().replace(' ', '_')}.json")


def get_disease_context(plant_name: str, disease_name: str, max_sources: int = 5,
                         environment: dict = None, top_k_per_section: int = 6) -> dict:
    """
    Returns a compact dict of {symptoms, causes, treatments,
    prevention, sources} for this plant+disease, using a cached
    scrape pool when available. `environment` (e.g. the latest
    sensor snapshot) is used to relevance-rank the sentences within
    each section - pass it in so "dry soil" conditions surface
    watering-related treatment sentences first, etc.
    """
    cache_file = _cache_path(plant_name, disease_name)
    combined = None

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                combined = json.load(f)
            logger.info(f"Using cached disease scrape pool for {plant_name} / {disease_name}")
        except (json.JSONDecodeError, OSError):
            combined = None  # fall through and re-scrape

    if combined is None:
        combined = _scrape_disease_pool(plant_name, disease_name, max_sources)
        try:
            with open(cache_file, "w") as f:
                json.dump(combined, f, indent=2)
        except OSError as e:
            logger.warning(f"Could not write disease cache: {e}")

    query_context = f"{plant_name} {disease_name} " + " ".join(
        f"{k} {v}" for k, v in (environment or {}).items() if isinstance(v, (int, float, str))
    )

    ranked = dict(combined)
    for key in ("symptoms", "causes", "treatments", "prevention"):
        ranked[key] = _rank_by_relevance(combined.get(key, []), query_context, top_k_per_section)

    return ranked


def _scrape_disease_pool(plant_name: str, disease_name: str, max_sources: int) -> dict:
    """Does the actual scraping and returns the full (unranked, deduped) pool
    of extracted sentences per section - this is what gets cached to disk."""

    query = f"{plant_name} {disease_name} disease symptoms treatment prevention"
    urls = _search(query, num_results=15)
    trusted_urls = [u for u in urls if _is_trusted(u)] or urls[:5]

    combined = {"symptoms": [], "causes": [], "treatments": [], "prevention": [], "sources": []}

    for url in trusted_urls[:max_sources]:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else url
            content = _extract_content(soup)
            sections = _extract_sections(content)

            for key in ("symptoms", "causes", "treatments", "prevention"):
                combined[key].extend(sections[key])
            combined["sources"].append({"url": url, "title": title})
        except requests.RequestException as e:
            logger.warning(f"Could not fetch {url}: {e}")
            continue

    # Keep a slightly larger pool (16) than the final ranked output
    # (top_k_per_section, default 6) so relevance ranking has
    # something meaningful to choose between.
    for key in ("symptoms", "causes", "treatments", "prevention"):
        combined[key] = list(dict.fromkeys(combined[key]))[:16]

    combined["plant"] = plant_name
    combined["disease"] = disease_name
    combined["fetched_at"] = datetime.now().isoformat()

    return combined


def search_local_context(query: str, plant_name: str = None, top_k: int = 2) -> dict:
    """Search existing disease cache and reuse CAG ranking without scraping/writes."""
    from pathlib import Path
    query_terms = set(re.findall(r"\w+", query.lower())) - {"what", "is", "the", "a", "of", "how", "my", "in", "does", "should"}
    candidates = []
    for path in Path(config.DISEASE_CACHE_DIR).glob("*/*.json"):
        if plant_name and path.parent.name != plant_name.lower().replace(" ", "_"):
            continue
        try:
            if path.stat().st_size > 500_000:
                continue
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(raw, dict):
            continue
        sections = {key: [s for s in raw.get(key, []) if isinstance(s, str)]
                    for key in ("symptoms", "causes", "treatments", "prevention")
                    if isinstance(raw.get(key, []), list)}
        terms = set(re.findall(r"\w+", (str(raw.get("disease", path.stem)).replace("_", " ") + " " + " ".join(s for values in sections.values() for s in values)).lower()))
        score = len(query_terms & terms)
        if score and any(sections.values()):
            ranked = {key: [s[:900] for s in _rank_by_relevance(values, query, 3)] for key, values in sections.items()}
            sources = raw.get("sources", [])
            candidates.append((score, {"plant": raw.get("plant", path.parent.name), "disease": raw.get("disease", path.stem), "cache_file": str(path.relative_to(config.DISEASE_CACHE_DIR)), "sections": ranked, "sources": sources[:3] if isinstance(sources, list) else [], "fetched_at": raw.get("fetched_at")}))
    candidates.sort(key=lambda item: item[0], reverse=True)
    matches = [item[1] for item in candidates[:max(1, min(top_k, 3))]]
    return {"available": bool(matches), "matches": matches, "source": "local"}
