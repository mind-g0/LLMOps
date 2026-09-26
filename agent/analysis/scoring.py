"""Score, confidence and triage: pure functions. The LLM only supplies qualitative verdicts;
the number a recruiter sees is computed here, so the same CV gives the same score every time."""
from agent.state import Flag, SkillVerdict
from config import settings as S

_SKILL_CREDIT = {"met": 1.0, "partial": 0.5, "missing": 0.0}
_RELEVANCE = {"strong": 1.0, "partial": 0.5, "weak": 0.15}
_EDU = {"meets": 1.0, "related": 0.6, "unrelated": 0.2, "not_required": 1.0}
_PROJ = {"strong": 1.0, "some": 0.6, "none": 0.2}


def coverage(verdicts: list[SkillVerdict], importance: str) -> float | None:
    vs = [v for v in verdicts if v.importance == importance]
    return sum(_SKILL_CREDIT[v.verdict] for v in vs) / len(vs) if vs else None


def skills_component(verdicts: list[SkillVerdict]) -> float:
    req, nice = coverage(verdicts, "required"), coverage(verdicts, "nice")
    if req is None and nice is None:
        return 0.0
    if nice is None:
        return req  # type: ignore[return-value]
    if req is None:
        return nice
    w = S.NICE_TO_HAVE_WEIGHT
    return (1 - w) * req + w * nice


def experience_component(years: float, min_years: float, relevance: str) -> float:
    ratio = 1.0 if min_years <= 0 else min(years / min_years, 1.0)
    return 0.5 * ratio + 0.5 * _RELEVANCE[relevance]


def compute_score(verdicts, years, min_years, relevance, education_fit, projects_certs, education_required: bool):
    edu = _EDU[education_fit] if education_required else 1.0
    parts = {
        "experience": experience_component(years, min_years, relevance),
        "skills": skills_component(verdicts),
        "education": edu,
        "projects_certs": _PROJ[projects_certs],
    }
    weights = S.SCORE_WEIGHTS
    breakdown = {k: round(parts[k] * weights[k], 1) for k in parts}
    return round(sum(breakdown.values()), 1), breakdown


def match_confidence(parse_conf: float, embed_cov: float, final_cov: float, completeness: float, n_flags: int) -> float:
    """Blend of parse quality, agreement between embedding and LLM-informed skill coverage,
    field completeness, and a penalty per anomaly flag."""
    agreement = 1.0 - abs(embed_cov - final_cov)
    conf = 0.4 * parse_conf + 0.3 * agreement + 0.3 * completeness - 0.1 * min(n_flags, 3)
    return round(max(0.0, min(1.0, conf)), 3)


def triage(score: float, confidence: float, flags: list[Flag]) -> tuple[str, list[str]]:
    """Plain conditional, not an agent. Thresholds come from settings (calibrate on the eval set)."""
    reasons: list[str] = [f.code for f in flags]
    if confidence < S.TRIAGE_MIN_CONFIDENCE:
        reasons.append("low_confidence")
    if reasons:
        return "review", reasons
    if score >= S.TRIAGE_ACCEPT_SCORE:
        return "auto_accept", []
    if score <= S.TRIAGE_REJECT_SCORE:
        return "auto_reject", []
    return "review", ["mid_score"]
