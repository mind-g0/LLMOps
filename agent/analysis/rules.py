"""Deterministic profile logic: experience years, anomaly flags, extraction confidence."""
from agent.state import CandidateProfile, Flag, WorkExperience
from config import settings as S
from utils.text import current_year


def _intervals(experience: list[WorkExperience], today: int) -> list[tuple[int, int]]:
    out = []
    for e in experience:
        if e.start_year is None:
            continue
        end = today if (e.is_current or e.end_year is None) else e.end_year
        if end < e.start_year:  # invalid; flagged separately
            continue
        out.append((e.start_year, end))
    return out


def compute_experience_years(experience: list[WorkExperience], today: int | None = None) -> float:
    """Union of date ranges (overlapping roles are not double counted). Year granularity."""
    today = today or current_year()
    merged: list[list[int]] = []
    for s, e in sorted(_intervals(experience, today)):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    total = 0.0
    for s, e in merged:
        total += (e - s) if e > s else 0.5
    return round(total, 1)


def detect_anomalies(profile: CandidateProfile, today: int | None = None) -> list[Flag]:
    """Code replacement for the evaluator prompt's 'Needs Human Review' anomaly list."""
    today = today or current_year()
    flags: list[Flag] = []
    ex = profile.experience

    for e in ex:
        if e.start_year and e.end_year and e.end_year < e.start_year:
            flags.append(Flag(code="date_order", detail=f"{e.title}: {e.start_year}->{e.end_year}"))
        if (e.start_year and e.start_year > today) or (e.end_year and e.end_year > today + 1):
            flags.append(Flag(code="future_date", detail=e.title))

    raw = sum((e - s) for s, e in _intervals(ex, today))
    merged = compute_experience_years(ex, today)
    if raw - merged > 2:
        flags.append(Flag(code="overlap_employment", detail=f"raw={raw:.1f}y merged={merged:.1f}y"))

    stated = profile.stated_total_years
    if stated is not None and abs(stated - merged) > 3:
        flags.append(Flag(code="stated_vs_computed_years", detail=f"stated={stated} computed={merged}"))
    return flags


def completeness(profile: CandidateProfile) -> float:
    checks = [
        bool(profile.name.strip()),
        bool(profile.email or profile.phone),
        bool(profile.skills),
        bool(profile.experience),
        bool(profile.education),
    ]
    return sum(checks) / len(checks)


def parse_confidence(profile: CandidateProfile, text_ok: bool, ungrounded_ratio: float) -> float:
    """0-1. Penalises missing fields, unverifiable (scanned) parses and skills absent from the source."""
    conf = 0.35 + 0.65 * completeness(profile)
    if not text_ok:
        conf -= 0.15  # no machine-readable text layer: skills cannot be grounded
    conf -= 0.4 * ungrounded_ratio
    if profile.parse_method == "vision" and text_ok:
        conf -= 0.05  # text path failed validation and had to escalate
    return round(max(0.0, min(1.0, conf)), 3)


def max_ungrounded() -> float:
    return S.MAX_UNGROUNDED_SKILL_RATIO
