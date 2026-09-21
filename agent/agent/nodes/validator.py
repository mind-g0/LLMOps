"""Validation node (no LLM). Same role as the weather agent's validator: cheap code checks decide
whether extraction is trustworthy; only failures cost another GPU call.

Checks: required fields, grounding (skills/name must appear in the document text), confidence.
"""
from agent.logger import log_node
from agent.state import Flag, HRState, RDEMError
from analysis.rules import detect_anomalies, max_ungrounded, parse_confidence
from config import settings as S
from utils.text import normalize_text, resolve_target_language


@log_node
def validator(state: HRState) -> dict:
    p = state.profile
    attempts = state.extract_attempts
    can_retry = attempts < S.MAX_EXTRACT_ATTEMPTS and bool(state.page_paths) and not state.use_vision

    if p is None:
        if attempts < S.MAX_EXTRACT_ATTEMPTS and (state.page_paths or state.text_layer):
            return {"retry_extract": True, "use_vision": bool(state.page_paths), "_status": "retry"}
        rdem = RDEMError(node="validator", error_type="no_profile", attempt=attempts,
                         message="Extraction produced no profile after all attempts.",
                         suggestion="Route the CV to manual review.")
        return {"status": "failed", "retry_extract": False, "global_error_log": [rdem], "_status": "error"}

    issues: list[str] = []
    if not p.name.strip():
        issues.append("missing_name")
    if not p.skills:
        issues.append("no_skills")
    if not (p.experience or p.education):
        issues.append("no_experience_or_education")

    ungrounded: list[str] = []
    ratio = 0.0
    if state.text_ok:
        doc = normalize_text(state.text_layer)
        ungrounded = [s for s in p.skills if normalize_text(s) and normalize_text(s) not in doc]
        ratio = len(ungrounded) / len(p.skills) if p.skills else 0.0
        if ratio > max_ungrounded():
            issues.append("skills_not_in_source")
        if p.name.strip() and normalize_text(p.name) not in doc:
            issues.append("name_not_in_source")

    if issues and can_retry:
        return {"retry_extract": True, "use_vision": True, "validation_issues": issues, "_status": "retry"}

    flags = list(p.flags) + detect_anomalies(p)
    if issues:  # attempts exhausted: proceed, but force human review
        flags.append(Flag(code="unresolved_validation", detail=",".join(issues)))

    updated = p.model_copy(update={
        "ungrounded_skills": ungrounded,
        "raw_parse_confidence": parse_confidence(p, state.text_ok, ratio),
        "flags": flags,
    })
    target = resolve_target_language(p.detected_language, p.dominant_language, state.output_language)
    return {"profile": updated, "retry_extract": False, "validation_issues": issues, "target_language": target,
            "_status": "success" if not issues else "flagged"}
