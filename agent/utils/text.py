"""Language-agnostic text helpers: script detection, Arabic normalisation, year coercion."""
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Literal, Optional

Lang = Literal["en", "ar", "mixed"]

_AR_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_AR_PRESENTATION_RE = re.compile(r"[\uFB50-\uFDFF\uFE70-\uFEFF]")
_LATIN_RE = re.compile(r"[A-Za-z]")
_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
_EASTERN = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_ALEF = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})
_KEEP_RE = re.compile(r"[^\w+#.\s]", re.UNICODE)


def current_year() -> int:
    return datetime.now(timezone.utc).year


def to_western_digits(s: str) -> str:
    return s.translate(_EASTERN)


def normalize_text(s: str) -> str:
    """Canonical form for comparing skills / grounding quotes across EN and AR."""
    s = unicodedata.normalize("NFKC", s or "")
    s = to_western_digits(s).lower()
    s = s.replace("\u0640", "")  # tatweel
    s = _DIACRITICS_RE.sub("", s).translate(_ALEF)
    s = _KEEP_RE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.strip(".")


def script_counts(text: str) -> tuple[int, int]:
    return len(_AR_RE.findall(text or "")), len(_LATIN_RE.findall(text or ""))


def arabic_ratio(text: str) -> float:
    ar, lat = script_counts(text)
    return ar / (ar + lat) if (ar + lat) else 0.0


def detect_language(text: str) -> Lang:
    """Script-ratio detection. Deterministic and reliable for the EN/AR pair."""
    ar, lat = script_counts(text)
    if ar + lat == 0:
        return "en"
    ratio = ar / (ar + lat)
    if ratio >= 0.75:
        return "ar"
    if ratio <= 0.15:
        return "en"
    return "mixed"


def dominant_language(text: str) -> Literal["en", "ar"]:
    ar, lat = script_counts(text)
    return "ar" if ar > lat else "en"


def resolve_target_language(detected: Lang, dominant: str, override: Optional[str]) -> Literal["en", "ar"]:
    """Mixed-CV rule (documented): explicit override > detected language > dominant script."""
    if override in ("en", "ar"):
        return override  # type: ignore[return-value]
    if detected in ("en", "ar"):
        return detected  # type: ignore[return-value]
    return "ar" if dominant == "ar" else "en"


def language_matches(text: str, target: str) -> bool:
    """Pass/fail check that generated text is in the target language."""
    ratio = arabic_ratio(text)
    return ratio >= 0.5 if target == "ar" else ratio <= 0.1


def presentation_form_ratio(text: str) -> float:
    """High share of Arabic presentation forms usually means a legacy/garbled PDF text layer."""
    ar = len(_AR_RE.findall(text or ""))
    return len(_AR_PRESENTATION_RE.findall(text or "")) / ar if ar else 0.0


def alnum_ratio(text: str) -> float:
    s = re.sub(r"\s+", "", text or "")
    return sum(ch.isalnum() for ch in s) / len(s) if s else 0.0


def hijri_to_gregorian_year(h: int) -> int:
    return round(h * 0.970224 + 621.5774)


_PRESENT = {"present", "current", "now", "ongoing", "الان", "الآن", "حتى الان", "حاليا", "حالياً", "الي الان"}


def coerce_year(v: Any) -> Optional[int]:
    """Robust year parsing: Eastern digits, 'present', Hijri years, garbage -> None."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, str):
        raw = v.strip().lower()
        if raw in _PRESENT:
            return None
        m = re.search(r"\d{4}", to_western_digits(raw))
        if not m:
            return None
        v = int(m.group())
    try:
        y = int(v)
    except (TypeError, ValueError):
        return None
    if 1370 <= y <= 1500:  # Hijri
        y = hijri_to_gregorian_year(y)
    return y if 1950 <= y <= 2100 else None
