"""Extraction agent. Cheap path first: text layer -> one guided call. Escalates to the VLM on page
images when the validator rejects the text path (the retry is an *escalation*, not a re-roll).
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
    vision = state.use_vision or not state.text_ok
    if vision and not state.page_paths:  # nothing to look at (e.g. txt/docx without soffice)
        vision = False
    text = state.text_layer if (state.text_ok or not vision) else ""
    if vision and state.text_ok:
        text = state.text_layer  # usable text is passed as a hint alongside the images

    get_logger().info(f"  [extractor] attempt={attempt} mode={'vision' if vision else 'text'}")
    try:
        ext = _call_extract(vision, state.page_paths, text)
        return {"profile": build_profile(ext, state, vision), "extract_attempts": attempt}
    except Exception as e:
        rdem = RDEMError(node="extractor", error_type="extraction_failed", attempt=attempt,
                         message=f"{type(e).__name__}: {str(e)[:300]}",
                         suggestion="Escalate to vision or flag for manual review.")
        return {"extract_attempts": attempt, "global_error_log": [rdem], "_status": "error"}
