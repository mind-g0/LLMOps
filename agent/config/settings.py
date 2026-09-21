"""Central configuration. Every tunable lives here and can be overridden via .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}

# ── Models (self-hosted, OpenAI-compatible vLLM endpoints) ─────────────────
VLM_API_BASE = _env("VLM_API_BASE", "")
VLM_MODEL = _env("VLM_MODEL", "")  # multilingual (AR/EN)
# Qwen advises against greedy decoding for thinking models; confirm on the model card.
VLM_TEMPERATURE = _float("VLM_TEMPERATURE", 0.6)
VLM_MAX_TOKENS = _int("VLM_MAX_TOKENS", 8192)  # thinking tokens count toward this

LLM_API_BASE = _env("LLM_API_BASE", "")
LLM_MODEL = _env("LLM_MODEL", "")  # multilingual (AR/EN)

LLM_TEMPERATURE = _float("LLM_TEMPERATURE", 0.0)
LLM_MAX_TOKENS = _int("LLM_MAX_TOKENS", 4096)
LLM_ENABLE_THINKING = _bool("LLM_ENABLE_THINKING", False)

# Same served model as LLM, but thinking ON (toggled per request, so no extra GPU memory).
REASONER_TEMPERATURE = _float("REASONER_TEMPERATURE", 0.6)
REASONER_MAX_TOKENS = _int("REASONER_MAX_TOKENS", 8192)

API_KEY = _env("LLM_API_KEY", "EMPTY")
LM_TIMEOUT = _int("LM_TIMEOUT", 180)
DSPY_CACHE = _bool("DSPY_CACHE", False)  # keep False while benchmarking latency

# "vlm" = Qwen3-VL reads the text layer too; "llm" = Qwen3.5 does text-only extraction.
TEXT_EXTRACTION_MODEL = _env("TEXT_EXTRACTION_MODEL", "ocr")

# ── Ingestion ──────────────────────────────────────────────────────────────
TMP_DIR = BASE_DIR / "tmp"
PAGE_MAX_SIDE = _int("PAGE_MAX_SIDE", 1800)
PAGE_RENDER_SCALE = _float("PAGE_RENDER_SCALE", 2.5)
MAX_PAGES = _int("MAX_PAGES", 6)
# "simple": no OCR, no table model (a scan yields no text -> the VLM takes over)  [default]
# "tables": no OCR, table structure on      "full": library defaults incl. OCR
DOCLING_MODE = _env("DOCLING_MODE", "simple")
MIN_TEXT_CHARS = _int("MIN_TEXT_CHARS", 300)
MIN_ALNUM_RATIO = _float("MIN_ALNUM_RATIO", 0.6)
MAX_PRESENTATION_FORM_RATIO = _float("MAX_PRESENTATION_FORM_RATIO", 0.3)
MAX_EXTRACT_ATTEMPTS = _int("MAX_EXTRACT_ATTEMPTS", 2)
MAX_UNGROUNDED_SKILL_RATIO = _float("MAX_UNGROUNDED_SKILL_RATIO", 0.3)

# ── Vector store ───────────────────────────────────────────────────────────
QDRANT_URL = _env("QDRANT_URL", "")  # e.g. http://qdrant:6333 ; empty -> embedded local mode
QDRANT_API_KEY = _env("QDRANT_API_KEY", "")
QDRANT_PATH = Path(_env("QDRANT_PATH", str(BASE_DIR / "vectorstore" / "qdrant_db")))
EMBEDDING_MODEL = _env("EMBEDDING_MODEL", "BAAI/bge-m3")  # multilingual (AR/EN)
EMBEDDING_DIM = _int("EMBEDDING_DIM", 1024)
EMBEDDING_DEVICE = _env("EMBEDDING_DEVICE", "cpu")
JOBS_COLLECTION = "hr_jobs"
CANDIDATES_COLLECTION = "hr_candidates"
CATALOG_COLLECTION = "course_catalog"
WEB_CACHE_COLLECTION = "web_search_cache"
MATCH_TOP_K = _int("MATCH_TOP_K", 50)

# ── Skill matching (calibrate on the eval set, do not trust defaults) ──────
SKILL_SIM_MET = _float("SKILL_SIM_MET", 0.82)     # >= : same skill, no LLM needed
SKILL_SIM_AMBIG = _float("SKILL_SIM_AMBIG", 0.60)  # between: LLM judges; < : missing
NICE_TO_HAVE_WEIGHT = _float("NICE_TO_HAVE_WEIGHT", 0.2)
EVIDENCE_TOP_K = _int("EVIDENCE_TOP_K", 3)
# "react": thinking + tool loop over the whole CV for every skill code could not confirm.
# "hybrid": single guided call, only for the ambiguous embedding band (cheaper; use for the ablation).
GAP_MODE = _env("GAP_MODE", "react")
GAP_MAX_ITERS = _int("GAP_MAX_ITERS", 5)
GAP_WORKERS = _int("GAP_WORKERS", 3)

# ── Scoring rubric (from the team's evaluator; computed in code, not by the LLM) ──
SCORE_WEIGHTS = {"experience": 35.0, "skills": 30.0, "education": 20.0, "projects_certs": 15.0}

# ── Triage ─────────────────────────────────────────────────────────────────
TRIAGE_ACCEPT_SCORE = _float("TRIAGE_ACCEPT_SCORE", 75.0)
TRIAGE_REJECT_SCORE = _float("TRIAGE_REJECT_SCORE", 40.0)
TRIAGE_MIN_CONFIDENCE = _float("TRIAGE_MIN_CONFIDENCE", 0.70)

# ── Recommendation ─────────────────────────────────────────────────────────
ENABLE_RECOMMENDATIONS = _bool("ENABLE_RECOMMENDATIONS", True)
MAX_RECOMMEND_SKILLS = _int("MAX_RECOMMEND_SKILLS", 5)
RECOMMEND_MAX_ITERS = _int("RECOMMEND_MAX_ITERS", 4)
RECOMMEND_WORKERS = _int("RECOMMEND_WORKERS", 3)
CATALOG_MIN_SCORE = _float("CATALOG_MIN_SCORE", 0.55)
TAVILY_API_KEY = _env("TAVILY_API_KEY", "")
WEB_CACHE_TTL_DAYS = _float("WEB_CACHE_TTL_DAYS", 7)
WEB_CACHE_MIN_SIM = _float("WEB_CACHE_MIN_SIM", 0.90)

# ── Backend integration ─────────────────────────────────────────────────────
BACKEND_API_BASE = _env("BACKEND_API_BASE", "")  # e.g. http://localhost:8004

# ── Observability ──────────────────────────────────────────────────────────
LOG_DIR = BASE_DIR / "logs"
# CVs are personal data. Full prompts/outputs are written to logs ONLY if this is on.
LOG_PROMPTS = _bool("LOG_PROMPTS", False)
RESULT_DIR = BASE_DIR / "result"
