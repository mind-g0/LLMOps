"""Formatter: deterministic (no LLM). Always emits a structured HRReport, even for failures, so the
caller never has to handle a crash. Human-readable text uses localised labels in the target language."""
from agent.logger import log_node
from agent.state import Flag, HRReport, HRState

LABELS = {
    "en": {
        "title": "Candidate Evaluation Report", "candidate": "Candidate", "job": "Job", "score": "Match score",
        "confidence": "Confidence", "decision": "Suggested action", "why": "Justification",
        "breakdown": "Score breakdown", "met": "Skills met", "partial": "Partial skills", "missing": "Missing skills",
        "recs": "Learning recommendations", "source": "Source", "review": "Review reasons", "flags": "Flags",
        "failed": "Evaluation failed", "unresolved": "No resource found for",
        "cv_preview": "Candidate CV Preview", "job_requirement": "Target Job Requirement",
        "eval_metrics": "Evaluation Metrics", "strengths": "Strengths", "gaps": "Gaps & Missing Skills",
        "recommendation": "Recommendation",
        "buckets": {"auto_accept": "Auto-accept", "auto_reject": "Auto-reject", "review": "Needs human review"},
        "codes": {
            "overlap_employment": "Overlapping employment periods",
            "stated_vs_computed_years": "Stated experience differs from computed",
            "date_order": "End date before start date", "future_date": "Date in the future",
            "unresolved_validation": "Extraction checks not fully resolved",
            "output_language_mismatch": "Output language does not match target",
            "assessment_failed": "Qualitative assessment failed", "justification_failed": "Justification failed",
            "low_confidence": "Low confidence", "mid_score": "Mid-range score",
            "job_has_no_required_skills": "No required skills configured for this job",
            "not_a_cv": "Document does not appear to be a CV",
        },
    },
    "ar": {
        "title": "تقرير تقييم المرشح", "candidate": "المرشح", "job": "الوظيفة", "score": "درجة المطابقة",
        "confidence": "مستوى الثقة", "decision": "الإجراء المقترح", "why": "التبرير",
        "breakdown": "تفصيل الدرجة", "met": "المهارات المتوفرة", "partial": "المهارات الجزئية", "missing": "المهارات المفقودة",
        "recs": "التوصيات التعليمية", "source": "المصدر", "review": "أسباب المراجعة", "flags": "تنبيهات",
        "failed": "فشل التقييم", "unresolved": "لم يتم العثور على مورد لـ",
        "cv_preview": "معاينة السيرة الذاتية للمرشح", "job_requirement": "متطلبات الوظيفة المستهدفة",
        "eval_metrics": "مقاييس التقييم", "strengths": "نقاط القوة", "gaps": "الفجوات والمهارات المفقودة",
        "recommendation": "التوصية",
        "buckets": {"auto_accept": "قبول تلقائي", "auto_reject": "رفض تلقائي", "review": "يحتاج مراجعة بشرية"},
        "codes": {
            "overlap_employment": "تداخل في فترات العمل",
            "stated_vs_computed_years": "اختلاف بين سنوات الخبرة المذكورة والمحسوبة",
            "date_order": "تاريخ النهاية قبل تاريخ البداية", "future_date": "تاريخ في المستقبل",
            "unresolved_validation": "لم تُحل جميع فحوصات الاستخراج",
            "output_language_mismatch": "لغة المخرجات لا تطابق اللغة المستهدفة",
            "assessment_failed": "فشل التقييم النوعي", "justification_failed": "فشل إنشاء التبرير",
            "low_confidence": "ثقة منخفضة", "mid_score": "درجة متوسطة",
            "job_has_no_required_skills": "لا توجد مهارات مطلوبة محددة لهذه الوظيفة",
            "not_a_cv": "المستند لا يبدو أنه سيرة ذاتية",
        },
    },
}


def humanize_code(lang: str, code: str) -> str:
    """Human-readable label for a review/flag code, in the given language. Unknown codes pass through."""
    return LABELS[lang]["codes"].get(code, code)


def render_markdown(r: HRReport) -> str:
    L = LABELS[r.target_language]
    code = lambda c: humanize_code(r.target_language, c)  # noqa: E731
    out = [f"# {L['title']}", ""]
    if r.status != "ok" or not r.match or not r.profile:
        out.append(f"**{L['failed']}**")
        out += [f"- `{e.error_type}`: {e.message}" for e in r.errors]
        return "\n".join(out)
    p, m, g = r.profile, r.match, r.skill_gap
    out += [f"## {L['cv_preview']}",
            f"Name: {p.name or 'N/A'}",
            f"Location: {p.location or 'N/A'}",
            f"Contact: {p.email or 'N/A'} | {p.phone or 'N/A'}",
            "Links:"]
    links = {"GitHub": "N/A", "LinkedIn": "N/A", "Portfolio": "N/A"}
    for link in p.links:
        lower = link.lower()
        kind = "GitHub" if "github" in lower else "LinkedIn" if "linkedin" in lower else "Portfolio"
        links[kind] = link
    out += [f"- {kind}: {value}" for kind, value in links.items()]
    out += [f"Languages: {', '.join(p.spoken_languages) if p.spoken_languages else 'N/A'}",
            "Skills:", *[f"- {skill}" for skill in p.skills]]

    out += ["Education:"]
    if p.education:
        out += [f"- {x.degree or 'N/A'} in {x.field_of_study or 'N/A'} at {x.institution or 'N/A'}"
                f" ({x.graduation_year or 'N/A'})" for x in p.education]
    else:
        out.append("- None listed")

    out += [f"Experience ({p.experience_years:.1f} YOE):"]
    if p.experience:
        out += [f"- {x.title} at {x.company or 'N/A'} ({x.start_year or 'N/A'} - "
                f"{'Present' if x.is_current else x.end_year or 'N/A'})"
                + (f": {x.description}" if x.description else "") for x in p.experience]
    else:
        out.append("- None listed")

    out += ["Projects:"]
    if p.projects:
        out += [f"- {x.name or 'Unnamed project'}: {x.description or 'N/A'}"
                + (f" [Tech: {', '.join(x.technologies)}]" if x.technologies else "") for x in p.projects]
    else:
        out.append("- None listed")

    out += ["Certifications:"]
    if p.certifications:
        out += [f"- {x.title} ({x.issuer or 'N/A'}, {x.year or 'N/A'})" for x in p.certifications]
    else:
        out.append("- None listed")

    out += ["", f"Summary: {p.summary or 'None listed'}", "",
            f"## {L['job_requirement']}", f"Tag: {r.job_id}", f"Title: {r.job_title or r.job_id}",
            f"Required skills: {', '.join(r.required_skills) if r.required_skills else 'None listed'}"]
    if r.nice_to_have_skills:
        out.append(f"Nice-to-have skills: {', '.join(r.nice_to_have_skills)}")

    met = [v.skill for v in g.verdicts if v.verdict == "met"] if g else []
    partial = [v.skill for v in g.verdicts if v.verdict == "partial"] if g else []
    missing = g.missing_skills if g else []
    strengths = met + partial
    out += ["", f"## {L['eval_metrics']}", f"Match Score: {m.match_score:.1f}%",
            f"Decision: {L['buckets'][m.triage_bucket]}",
            "", f"## {L['strengths']}"]
    out += [f"- Verified skill: {skill}" for skill in strengths]
    if p.experience:
        out.append(f"- {p.experience_years:.1f} years of computed experience")
    if p.education:
        out.append(f"- Education listed: {p.education[0].degree or 'degree'}")
    if not strengths and not p.experience and not p.education:
        out.append("- None verified")

    out += ["", f"## {L['gaps']}"]
    out += [f"- Missing required skill: {skill}" for skill in missing]
    out += [f"- Partial skill requiring review: {skill}" for skill in partial]
    if p.flags or m.review_reasons:
        out += [f"- Review flag: {code(flag.code)}" for flag in p.flags]
        out += [f"- Review reason: {code(reason)}" for reason in m.review_reasons]
    if not missing and not partial and not p.flags and not m.review_reasons:
        out.append("- No verified gaps")

    recommendation = _recommendation(r, missing)
    out += ["", f"## {L['recommendation']}", recommendation]
    if r.recommendations or r.unresolved_skills:
        out += ["", f"## {L['recs']}"]
        for x in r.recommendations:
            out.append(f"- **{x.missing_skill}**: [{x.title}]({x.url}) ({x.provider}, {L['source']}: {x.source})\n  {x.reason}")
        out += [f"- {L['unresolved']} {s}" for s in r.unresolved_skills]
    if r.flags:
        out += ["", f"## {L['flags']}"] + [f"- {code(f.code)} {f.detail}".strip() for f in r.flags]
    text = "\n".join(out)
    return f'<div dir="rtl">\n\n{text}\n\n</div>' if r.target_language == "ar" else text


def _recommendation(report: HRReport, missing: list[str]) -> str:
    """Build a factual recommendation without asking an LLM to invent rationale."""
    bucket = report.match.triage_bucket
    if bucket == "auto_accept":
        return "Strong Match - Proceed to human review or the next hiring stage."
    if bucket == "auto_reject":
        return "Strong Reject - Mandatory requirements are not sufficiently evidenced."
    if missing:
        return "Needs Review - Verify the missing requirements and candidate evidence before deciding."
    return "Needs Review - The result has unresolved review conditions."


@log_node
def formatter(state: HRState) -> dict:
    timings: dict[str, float] = {}
    for s in state.audit_trail:
        timings[s.node_name] = round(timings.get(s.node_name, 0.0) + s.duration_s, 2)

    p = state.profile
    ok = state.status != "failed" and state.match is not None
    flags: list[Flag] = list(p.flags) if p else []
    report = HRReport(
        status="ok" if ok else "failed",
        candidate_id=state.candidate_id,
        job_id=state.job_id,
        job_version=state.job.requirement.job_version if state.job else "",
        job_title=state.job.requirement.title if state.job else "",
        required_skills=state.job.requirement.required_skills if state.job else [],
        nice_to_have_skills=state.job.requirement.nice_to_have_skills if state.job else [],
        detected_language=p.detected_language if p else "",
        target_language=state.target_language,
        parse_method=p.parse_method if p else "",
        profile=p, skill_gap=state.skill_gap, match=state.match,
        recommendations=state.recommendations, unresolved_skills=state.unresolved_skills,
        flags=flags, errors=state.global_error_log, timings_s=timings,
    )
    return {"report": report, "status": "ok" if ok else "failed"}
