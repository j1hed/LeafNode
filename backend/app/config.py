import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


DB_FILE = os.getenv("LEAFNODE_DB_FILE", str(BASE_DIR / "leafnode.db"))

PLANT_DATA_DIR = Path(os.getenv("PLANT_DATA_DIR", BASE_DIR / "plant_data"))
DISEASE_CACHE_DIR = Path(os.getenv("DISEASE_CACHE_DIR", BASE_DIR / "plant_diseases"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", BASE_DIR / "logs"))

for d in (PLANT_DATA_DIR, DISEASE_CACHE_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "lmstudio").lower()


LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = os.getenv("LMSTUDIO_MODEL", "local-model")

GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.4"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1200"))


WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY", "")
WEATHERAPI_LOCATION = os.getenv("WEATHERAPI_LOCATION", "Tunisia")

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_MAX_VIDEOS_PER_PLANT = int(os.getenv("YOUTUBE_MAX_VIDEOS_PER_PLANT", "3"))
YOUTUBE_TRANSCRIPT_LANGUAGES = os.getenv("YOUTUBE_TRANSCRIPT_LANGUAGES", "en,fr").split(",")


TRUSTED_DISEASE_DOMAINS = [
    "extension.umn.edu", "extension.umd.edu", "extension.psu.edu",
    "extension.cornell.edu", "ipm.ucanr.edu", "aces.illinois.edu",
    "hgic.clemson.edu", "ag.umass.edu", "hort.extension.wisc.edu",
    "extension.missouri.edu", "extension.purdue.edu", "extension.colostate.edu",
    "extension.oregonstate.edu", "extension.wsu.edu", "extension.uga.edu",
    "extension.ufl.edu", "extension.tennessee.edu", "extension.msstate.edu",
    "usda.gov", "ars.usda.gov", "nifa.usda.gov", "aphis.usda.gov",
    "rhs.org.uk", "missouribotanicalgarden.org", "chicagobotanic.org",
    "nybg.org", "arborday.org", "bbg.org", "plantclinic.cornell.edu",
    "gardeningknowhow.com", "almanac.com", "gardeners.com",
    "garden.org", "growveg.com", "finegardening.com", "bhg.com",
    "plantpath.cornell.edu", "plantpath.wisc.edu", "plantpath.ifas.ufl.edu",
    "plantpathology.ces.ncsu.edu", "plant-pest-advisory.rutgers.edu",
]


DISEASE_CONFIDENCE_THRESHOLD = float(os.getenv("DISEASE_CONFIDENCE_THRESHOLD", "70"))


KNOWN_DEVICES = {"pump", "fan", "peltier"}


WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8765"))
# Explicit frontend origins are required for credentialed browser requests.
CORS_ORIGINS = [origin.strip() for origin in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173"
).split(",") if origin.strip() and origin.strip() != "*"]
CHATBOT_STALE_SECONDS = int(os.getenv("CHATBOT_STALE_SECONDS", "300"))
