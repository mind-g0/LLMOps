"""Matcher agent. The LLM gives qualitative verdicts (enums); CODE turns them into the 0-100 score
using the team's rubric (Experience 35 / Skills 30 / Education 20 / Projects+Certs 15). Same CV, same
score, and every point is explainable. The justification is written in the candidate's language."""
import dspy

from agent.dspy_setup import lm_ctx
from agent.logger import get_logger, log_node
from agent.signatures import AssessFit, WriteJustification
from agent.state import CandidateProfile, Flag, HRState, JobContext, MatchResult
from analysis.rules import completeness
from analysis.scoring import compute_score, coverage, match_confidence, triage


def candidate_brief(p: CandidateProfile) -> str:
    parts = [f"Experience (computed {p.experience_years} years):"]
    parts += [f"- {e.title} @ {e.company} ({e.start_year}-{e.end_year or 'present'}): {e.description[:250]}" for e in p.experience]
    parts.append("Education:")
    parts += [f"- {e.degree} {e.field_of_study}, {e.institution} ({e.graduation_year})" for e in p.education]
    if p.projects:
        parts.append("Projects:")
        parts += [f"- {x.name}: {x.description[:200]}" for x in p.projects]
    if p.certifications:
        parts.append("Certifications:")
        parts += [f"- {c.title} ({c.issuer})" for c in p.certifications]
    return "\n".join(parts)


def job_summary(job: JobContext) -> str:
    r = job.requirement
    ev = "\n".join(f"[{c.section}] {c.text[:400]}" for c in job.chunks[:3])
    return f"Responsibilities: {r.responsibilities_summary}\nEducation requirement: {r.education_requirement or 'none'}\nEvidence:\n{ev}"


def _call_assess(job_title: str, summary: str, brief: str) -> tuple[str, str, str]:
    """Thin LLM boundary (patched in tests)."""
    with lm_ctx("llm"):
        r = dspy.Predict(AssessFit)(job_title=job_title, job_summary=summary, candidate_brief=brief)
    return r.experience_relevance, r.education_fit, r.projects_certs


def _call_justify(**kw) -> str:
    """Thin LLM boundary (patched in tests)."""
    with lm_ctx("llm"):
        return dspy.Predict(WriteJustification)(**kw).justification


def deterministic_justification(target: str, score: float, years: float, met: list[str],
                                 partial: list[str], missing: list[str]) -> str:
    """Build the factual explanation from validated fields; never ask an LLM to invent facts."""
    met_text = ", ".join(met) if met else "none"
    partial_text = ", ".join(partial) if partial else "none"
    missing_text = ", ".join(missing) if missing else "none"
    if target == "ar":
        return (f"درجة المطابقة {score:.1f}/100. الخبرة المحسوبة {years:.1f} سنة. "
                f"المهارات المتوفرة: {met_text}. المهارات الجزئية: {partial_text}. "
                f"المهارات المفقودة: {missing_text}.")
    return (f"Match score: {score:.1f}/100. Computed experience: {years:.1f} years. "
            f"Verified skills: {met_text}. Partial skills: {partial_text}. "
            f"Missing skills: {missing_text}.")


@log_node
def matcher(state: HRState) -> dict:
    p, job, gap, lang = state.profile, state.job, state.skill_gap, state.target_language
    req = job.requirement
    extra: list[Flag] = []
    if not gap.verdicts:
        extra.append(Flag(code="job_has_no_required_skills"))

    try:
        rel, edu, proj = _call_assess(req.title, job_summary(job), candidate_brief(p))
    except Exception as e:
        get_logger().warning(f"    assess failed ({type(e).__name__}); neutral defaults + review flag")
        rel, edu, proj = "partial", "related", "some"
        extra.append(Flag(code="assessment_failed"))

    score, breakdown = compute_score(gap.verdicts, p.experience_years, req.min_experience_years, rel, edu, proj,
                                     education_required=bool(req.education_requirement.strip()))
    final_cov = coverage(gap.verdicts, "required")
    conf = match_confidence(p.raw_parse_confidence, gap.embedding_only_coverage,
                            final_cov if final_cov is not None else gap.embedding_only_coverage,
                            completeness(p), len(p.flags) + len(extra))

    justification = deterministic_justification(
        lang, score, p.experience_years,
        [v.skill for v in gap.verdicts if v.verdict == "met"],
        gap.partial_skills,
        gap.missing_skills,
    )

    bucket, reasons = triage(score, conf, [*p.flags, *extra])
    return {"match": MatchResult(match_score=score, match_confidence=conf, breakdown=breakdown,
                                 justification=justification, triage_bucket=bucket, review_reasons=reasons)}
