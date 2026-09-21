"""Gap agent: code confirms what it can for free; a thinking ReAct agent investigates the rest.

  1. normalised exact match / embedding >= SKILL_SIM_MET     -> met (free, no LLM)
  2. everything else (GAP_MODE=react): a ReAct agent with THINKING enabled loops over the WHOLE CV
     (skills, experience, projects, certifications) with `search_cv`, and reads `job_context`.
     A low similarity to the *skills list* proves nothing: the skill may only appear inside a project.
  3. Verification loop: the quote must appear in the lines the agent actually retrieved. If not, the
     agent gets feedback and must search again (once); still unverifiable -> verdict downgraded.

GAP_MODE=hybrid keeps the cheaper single guided call (ambiguous band only) for the ablation.
"""
import contextvars
from concurrent.futures import ThreadPoolExecutor

import dspy

from agent.dspy_setup import lm_ctx
from agent.logger import get_logger, log_node
from agent.signatures import JudgeSkill, JudgeSkillAgent
from agent.state import CandidateProfile, HRState, JobChunk, SkillGap, SkillVerdict
from config import settings as S
from analysis.skills import embedding_only_coverage, prematch, top_evidence
from rag.embedder import embed
from utils.text import normalize_text


def evidence_lines(p: CandidateProfile) -> list[str]:
    lines = list(p.skills)
    lines += [f"{e.title} {e.company}: {e.description}".strip() for e in p.experience]
    lines += [f"{x.name}: {x.description} {' '.join(x.technologies)}".strip() for x in p.projects]
    lines += [f"{c.title} {c.issuer}".strip() for c in p.certifications]
    if p.summary:
        lines.append(p.summary)
    return [ln[:300] for ln in lines if ln.strip()]


def _call_judge(skill: str, evidence: str) -> tuple[str, str]:
    """Thin LLM boundary (patched in tests)."""
    with lm_ctx("llm"):
        pred = dspy.ChainOfThought(JudgeSkill)(required_skill=skill, candidate_evidence=evidence)
    return pred.verdict, pred.evidence_quote


def _judge_hybrid(skill: str, imp: str, best: str, sim: float, lines: list[str], vecs) -> SkillVerdict:
    ev = "\n".join(f"- {ln}" for ln in top_evidence(skill, lines, vecs))
    try:
        verdict, quote = _call_judge(skill, ev)
    except Exception as e:
        get_logger().warning(f"    judge failed for '{skill}' ({type(e).__name__}); conservative 'partial'")
        return SkillVerdict(skill=skill, importance=imp, verdict="partial", method="embedding",
                            matched_with=best, similarity=sim)
    # Anti-hallucination: a positive verdict needs a quote that really is in the evidence.
    # Unverifiable -> downgrade one level (met->partial, partial->missing).
    if verdict != "missing" and not (quote.strip() and normalize_text(quote) in normalize_text(ev)):
        verdict = {"met": "partial", "partial": "missing"}[verdict]
        quote = ""
    return SkillVerdict(skill=skill, importance=imp, verdict=verdict, method="llm",
                        matched_with=best, similarity=sim, evidence=quote)



# ── ReAct mode ──────────────────────────────────────────────────────────────
def make_gap_tools(lines: list[str], vecs, chunks: list[JobChunk], seen: list[str]):
    """Tools are closures: the CV and job are bound inside, the model can only query them."""

    def search_cv(query: str) -> str:
        """Search the candidate's CV (skills, experience, projects, certifications). The query can be a
        skill name, a synonym, a related technology, or the same term in Arabic or English.
        Returns the most relevant CV lines."""
        hits = top_evidence(query, lines, vecs, k=4)
        seen.extend(hits)
        return "\n".join(f"[{i}] {h}" for i, h in enumerate(hits, 1)) or "The CV has no content."

    def job_context(skill: str) -> str:
        """Return how the job posting describes this skill or requirement, to judge what level or which
        equivalents are acceptable."""
        n = normalize_text(skill)
        pick = [c for c in chunks if n and n in normalize_text(c.text)] or chunks[:1]
        return "\n".join(f"[{c.section}] {c.text[:500]}" for c in pick[:2]) or "No job context."

    return [search_cv, job_context]


def _call_react_judge(skill: str, lines: list[str], vecs, chunks: list[JobChunk], seen: list[str],
                      feedback: str) -> tuple[str, str]:
    """Thin LLM boundary (patched in tests). Thinking is ON; the tool loop is bounded by GAP_MAX_ITERS."""
    with lm_ctx("reasoner"):
        agent = dspy.ReAct(JudgeSkillAgent, tools=make_gap_tools(lines, vecs, chunks, seen), max_iters=S.GAP_MAX_ITERS)
        pred = agent(required_skill=skill, feedback=feedback)
    return pred.verdict, pred.evidence_quote


_FEEDBACK = ("Your evidence_quote was not found verbatim in the CV lines returned by search_cv. "
             "Search again and copy the quote exactly, or answer 'missing'.")


def _judge_react(skill, imp, best, sim, lines, vecs, chunks) -> SkillVerdict:
    seen: list[str] = []
    try:
        verdict, quote = _call_react_judge(skill, lines, vecs, chunks, seen, "")
        for attempt in (1, 2):
            verified = bool(quote.strip()) and normalize_text(quote) in normalize_text("\n".join(seen))
            if verdict == "missing" or verified:
                break
            if attempt == 1:  # verification loop: one round of feedback
                get_logger().info(f"    [gap] '{skill}': quote unverifiable, asking the agent to re-search")
                verdict, quote = _call_react_judge(skill, lines, vecs, chunks, seen, _FEEDBACK)
            else:
                verdict, quote = {"met": "partial", "partial": "missing"}[verdict], ""
    except Exception as e:
        get_logger().warning(f"    [gap] agent failed for '{skill}' ({type(e).__name__}); falling back to single call")
        return _judge_hybrid(skill, imp, best, sim, lines, vecs)
    return SkillVerdict(skill=skill, importance=imp, verdict=verdict, method="agent",
                        matched_with=best, similarity=sim, evidence=quote if verdict != "missing" else "")


@log_node
def gap_agent(state: HRState) -> dict:
    job, p = state.job.requirement, state.profile
    job_skills = [(s, "required") for s in job.required_skills] + [(s, "nice") for s in job.nice_to_have_skills]
    react = S.GAP_MODE == "react"

    decided, pending = prematch(job_skills, p.skills, escalate_low=react)
    judged: list[SkillVerdict] = []
    if pending:
        lines = evidence_lines(p)
        vecs = embed(lines)
        if react:
            chunks = state.job.chunks
            with ThreadPoolExecutor(max_workers=S.GAP_WORKERS) as ex:
                futs = [ex.submit(contextvars.copy_context().run, _judge_react, sk, imp, b, sim, lines, vecs, chunks)
                        for sk, imp, b, sim in pending]
                judged = [f.result() for f in futs]
        else:
            judged = [_judge_hybrid(sk, imp, b, sim, lines, vecs) for sk, imp, b, sim in pending]

    order = {(s, i): n for n, (s, i) in enumerate(job_skills)}
    verdicts = sorted(decided + judged, key=lambda v: order[(v.skill, v.importance)])
    gap = SkillGap(
        verdicts=verdicts,
        missing_skills=[v.skill for v in verdicts if v.verdict == "missing"],
        partial_skills=[v.skill for v in verdicts if v.verdict == "partial"],
        embedding_only_coverage=embedding_only_coverage(job_skills, p.skills),
    )
    get_logger().info(f"  [gap] mode={S.GAP_MODE} decided_by_code={len(decided)} investigated={len(judged)}")
    return {"skill_gap": gap}
