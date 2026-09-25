"""Extraction agent. Vision-first whenever page images exist: the VLM reads the actual page, with
Docling's text (when usable) passed alongside as a hint, so it can catch anything the text layer
missed (tables, layout-dependent info, icons/badges, etc.). Text-only is the fallback only when
there are no page images at all (txt/md/json, or a docx that couldn't be rendered because
LibreOffice isn't installed). A validation failure still gets one retry (same modality, a re-roll,
not an escalation, since vision is already the default).
Values are extracted in the CV's ORIGINAL language: no translation step, so no translation errors."""
import base64
from pathlib import Path

import dspy

from agent.dspy_setup import lm_ctx
from agent.logger import get_logger, log_node
from agent.signatures import ExtractFromPages, ExtractFromText
from agent.state import CandidateExtraction, CandidateProfile, HRState, RDEMError
from analysis.rules import compute_experience_years
from config import settings as S
from utils.text import detect_language, dominant_language

MAX_CV_CHARS = 15_000


def _to_image(path: str) -> dspy.Image:
    b64 = base64.b64encode(Path(path).read_bytes()).decode()
    return dspy.Image(f"data:image/png;base64,{b64}")


def _call_extract(vision: bool, page_paths: list[str], text: str) -> CandidateExtraction:
    """Thin LLM boundary (patched in tests). Guided decoding forces the CandidateExtraction schema."""
    text = text[:MAX_CV_CHARS]
    if vision:
        with lm_ctx("ocr"):
            return dspy.Predict(ExtractFromPages)(pages=[_to_image(p) for p in page_paths], text_layer=text).profile
    with lm_ctx(S.TEXT_EXTRACTION_MODEL):  # type: ignore[arg-type]
        return dspy.Predict(ExtractFromText)(cv_text=text).profile


def _flatten(ext: CandidateExtraction) -> dict[str, str]:
    return {
        "summary": ext.summary,
        "skills": " ".join(ext.skills),
        "experience": " ".join(f"{e.title} {e.company} {e.description}" for e in ext.experience),
        "education": " ".join(f"{e.degree} {e.field_of_study} {e.institution}" for e in ext.education),
    }


def build_profile(ext: CandidateExtraction, state: HRState, vision: bool) -> CandidateProfile:
    sections = _flatten(ext)
    basis = state.text_layer if (state.text_ok and not vision) else " ".join([ext.name, *sections.values()])
    return CandidateProfile(
        **ext.model_dump(),
        candidate_id=state.candidate_id,
        source_file=Path(state.cv_path).name,
        detected_language=detect_language(basis),
        dominant_language=dominant_language(basis),
        section_languages={k: detect_language(v) for k, v in sections.items() if v.strip()},
        experience_years=compute_experience_years(ext.experience),  # code, never the LLM
        parse_method="vision" if vision else "text",
    )


@log_node
def extractor(state: HRState) -> dict:
    attempt = state.extract_attempts + 1
    # Always prefer vision when we have page images: the VLM sees the real layout, Docling's text
    # (if usable) just rides along as a hint. Falls back to text-only when there is nothing to look
    # at (no page images), OR when VLM_MODEL isn't configured on this deployment — a missing/empty
    # model id must never turn into a 100%-failure loop for every CV; it degrades to the text path
    # instead (same as this node's original text-first behavior).
    vision = bool(state.page_paths)
    if vision and not S.VLM_MODEL:
        get_logger().warning("  [extractor] VLM_MODEL is not configured; falling back to text-only extraction")
        vision = False
    text = state.text_layer if (state.text_ok or not vision) else ""

    get_logger().info(f"  [extractor] attempt={attempt} mode={'vision' if vision else 'text'}")
    try:
        ext = _call_extract(vision, state.page_paths, text)
        return {"profile": build_profile(ext, state, vision), "extract_attempts": attempt}
    except Exception as e:
        rdem = RDEMError(node="extractor", error_type="extraction_failed", attempt=attempt,
                         message=f"{type(e).__name__}: {str(e)[:300]}",
                         suggestion="Escalate to vision or flag for manual review.")
        return {"extract_attempts": attempt, "global_error_log": [rdem], "_status": "error"}
