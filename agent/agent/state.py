"""Typed contracts between agents. No free text moves between nodes: everything is a Pydantic model.

Two layers of models:
  * *Extraction models* (CandidateExtraction, JobExtraction) are what the LLM is forced to emit
    through guided decoding. They contain only what the model can know.
  * *System models* (CandidateProfile, JobRequirement, ...) add fields computed by code
    (experience years, confidence, language, ids). The LLM never produces those.
"""
import operator
from datetime import datetime, timezone
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from utils.text import Lang, coerce_year

Year = Annotated[Optional[int], BeforeValidator(coerce_year)]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Errors / observability (pattern kept from the weather agent) ───────────
class RDEMError(BaseModel):
    """Structured error carrier used by every node."""

    node: str
    error_type: str
    message: str
    suggestion: str = ""
    attempt: int = 1


class AgentStep(BaseModel):
    node_name: str
    status: str
    error: Optional[RDEMError] = None
    timestamp: str = Field(default_factory=now_iso)
    duration_s: float = 0.0


class Flag(BaseModel):
    """A machine-readable reason a human should look at this candidate."""

    code: str
    detail: str = ""


# ── Candidate ──────────────────────────────────────────────────────────────
class WorkExperience(BaseModel):
    title: str = Field(description="Job title exactly as written, original language")
    company: str = Field(default="", description="Employer exactly as written")
    start_year: Year = Field(default=None, description="Start year as a 4-digit number, null if unknown")
    end_year: Year = Field(default=None, description="End year, null if current or unknown")
    is_current: bool = Field(default=False, description="True if the role is ongoing")
    description: str = Field(default="", description="Responsibilities/achievements, copied as written")


class ExtractedEducation(BaseModel):
    degree: str = ""
    field_of_study: str = ""
    institution: str = ""
    graduation_year: Year = None


class ExtractedProject(BaseModel):
    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)


class ExtractedCertification(BaseModel):
    title: str = ""
    issuer: str = ""
    year: Year = None


class CandidateExtraction(BaseModel):
    """What the VLM/LLM is forced to output. Values are copied in their ORIGINAL language."""

    name: str = Field(default="", description="Full name exactly as written in the CV")
    email: Optional[str] = None
    phone: Optional[str] = None
    location: str = ""
    links: list[str] = Field(default_factory=list, description="GitHub/LinkedIn/portfolio URLs")
    skills: list[str] = Field(default_factory=list, description="Individual skills/tools, one per item")
    experience: list[WorkExperience] = Field(default_factory=list)
    education: list[ExtractedEducation] = Field(default_factory=list)
    projects: list[ExtractedProject] = Field(default_factory=list)
    certifications: list[ExtractedCertification] = Field(default_factory=list)
    spoken_languages: list[str] = Field(default_factory=list)
    summary: str = Field(default="", description="Professional summary if the CV has one, else empty")
    stated_total_years: Optional[float] = Field(
        default=None, description="Total years of experience ONLY if the CV states it explicitly"
    )


class CandidateProfile(CandidateExtraction):
    """Extraction + everything computed by code."""

    candidate_id: str
    source_file: str
    detected_language: Lang = "en"
    dominant_language: Literal["en", "ar"] = "en"
    section_languages: dict[str, str] = Field(default_factory=dict)
    experience_years: float = 0.0  # computed from date ranges, never trusted from the LLM
    parse_method: Literal["text", "vision"] = "text"
    raw_parse_confidence: float = 0.0
    ungrounded_skills: list[str] = Field(default_factory=list)
    flags: list[Flag] = Field(default_factory=list)


# ── Job ────────────────────────────────────────────────────────────────────
class JobExtraction(BaseModel):
    title: str = Field(default="", description="Job title as written")
    required_skills: list[str] = Field(default_factory=list, description="Mandatory skills/tools, one per item")
    nice_to_have_skills: list[str] = Field(default_factory=list)
    min_experience_years: float = Field(default=0.0, description="Minimum years required, 0 if unspecified")
    education_requirement: str = Field(default="", description="Required degree/field, empty if none")
    language_requirements: list[str] = Field(default_factory=list)
    responsibilities_summary: str = Field(default="", description="2 sentences, same language as the posting")


class JobRequirement(JobExtraction):
    job_id: str
    job_version: str
    language: Lang = "en"


class JobChunk(BaseModel):
    section: str
    text: str


class JobContext(BaseModel):
    requirement: JobRequirement
    chunks: list[JobChunk] = Field(default_factory=list)


# ── Analysis outputs ───────────────────────────────────────────────────────
class SkillVerdict(BaseModel):
    skill: str
    importance: Literal["required", "nice"]
    verdict: Literal["met", "partial", "missing"]
    method: Literal["exact", "embedding", "llm", "agent"]
    matched_with: str = ""
    similarity: float = 0.0
    evidence: str = ""  # verbatim quote from the CV (verified in code) for llm verdicts


class SkillGap(BaseModel):
    verdicts: list[SkillVerdict]
    missing_skills: list[str] = Field(default_factory=list)
    partial_skills: list[str] = Field(default_factory=list)
    embedding_only_coverage: float = 0.0  # used for match_confidence (agreement signal)


class MatchResult(BaseModel):
    match_score: float  # 0-100, computed by code from the rubric
    match_confidence: float  # 0-1
    breakdown: dict[str, float]
    justification: str  # in target_language
    triage_bucket: Literal["auto_accept", "auto_reject", "review"]
    review_reasons: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    missing_skill: str
    title: str
    provider: str = ""
    url: str
    source: Literal["catalog", "web_search"]
    reason: str  # in target_language


class HRReport(BaseModel):
    status: Literal["ok", "failed"]
    candidate_id: str = ""
    job_id: str = ""
    job_version: str = ""
    job_title: str = ""
    required_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    detected_language: str = ""
    target_language: str = "en"
    parse_method: str = ""
    profile: Optional[CandidateProfile] = None
    skill_gap: Optional[SkillGap] = None
    match: Optional[MatchResult] = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    unresolved_skills: list[str] = Field(default_factory=list)
    flags: list[Flag] = Field(default_factory=list)
    errors: list[RDEMError] = Field(default_factory=list)
    timings_s: dict[str, float] = Field(default_factory=dict)


# ── Graph state ────────────────────────────────────────────────────────────
class HRState(BaseModel):
    # inputs
    cv_path: str
    job_id: str
    output_language: Optional[str] = None  # "en" | "ar" | None (auto)

    # retrieval
    job: Optional[JobContext] = None

    # ingest
    candidate_id: str = ""
    page_paths: list[str] = Field(default_factory=list)
    raw_text_layer: str = ""  # byproduct text from page rendering (pdf/docx); fallback for parser
    text_layer: str = ""
    text_ok: bool = False

    # extraction / validation
    profile: Optional[CandidateProfile] = None
    extract_attempts: int = 0
    use_vision: bool = False
    retry_extract: bool = False
    validation_issues: list[str] = Field(default_factory=list)

    # analysis
    target_language: Literal["en", "ar"] = "en"
    skill_gap: Optional[SkillGap] = None
    match: Optional[MatchResult] = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    unresolved_skills: list[str] = Field(default_factory=list)

    # output
    report: Optional[HRReport] = None
    status: Literal["running", "ok", "failed"] = "running"

    # observability: reducers let each node return only its NEW entries
    audit_trail: Annotated[list[AgentStep], operator.add] = Field(default_factory=list)
    global_error_log: Annotated[list[RDEMError], operator.add] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)
