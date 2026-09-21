"""Skill matching, language-agnostic: normalised exact match -> multilingual embeddings -> LLM only
for the ambiguous middle. 'React' and its Arabic transliteration land in the same bucket because
bge-m3 embeds both languages in one space."""
import numpy as np

from agent.state import SkillVerdict
from config import settings as S
from rag.embedder import embed
from utils.text import normalize_text


def prematch(job_skills: list[tuple[str, str]], cand_skills: list[str], escalate_low: bool = False):
    """job_skills: [(skill, importance)]. Returns (decided verdicts, ambiguous [(skill, importance, best, sim)])."""
    if not job_skills:
        return [], []
    norm_cand = {normalize_text(c): c for c in cand_skills if normalize_text(c)}
    decided: list[SkillVerdict] = []
    pending = []
    for skill, imp in job_skills:
        n = normalize_text(skill)
        if n in norm_cand:
            decided.append(SkillVerdict(skill=skill, importance=imp, verdict="met", method="exact",
                                        matched_with=norm_cand[n], similarity=1.0))
        else:
            pending.append((skill, imp))
    if not pending:
        return decided, []
    if not cand_skills:
        if escalate_low:  # skills may still be evidenced in experience text
            return decided, [(s, i, "", 0.0) for s, i in pending]
        return decided + [SkillVerdict(skill=s, importance=i, verdict="missing", method="embedding")
                          for s, i in pending], []

    sims = embed([s for s, _ in pending]) @ embed(cand_skills).T  # (pending, cand), unit vectors
    ambiguous = []
    for row, (skill, imp) in zip(sims, pending):
        j = int(np.argmax(row))
        sim = float(row[j])
        if sim >= S.SKILL_SIM_MET:
            decided.append(SkillVerdict(skill=skill, importance=imp, verdict="met", method="embedding",
                                        matched_with=cand_skills[j], similarity=round(sim, 3)))
        elif sim >= S.SKILL_SIM_AMBIG:
            ambiguous.append((skill, imp, cand_skills[j], round(sim, 3)))
        elif escalate_low:  # low similarity to the SKILLS LIST says nothing about the experience text
            ambiguous.append((skill, imp, cand_skills[j], round(sim, 3)))
        else:
            decided.append(SkillVerdict(skill=skill, importance=imp, verdict="missing", method="embedding",
                                        matched_with=cand_skills[j], similarity=round(sim, 3)))
    return decided, ambiguous


def top_evidence(skill: str, lines: list[str], line_vecs: np.ndarray, k: int | None = None) -> list[str]:
    if not lines:
        return []
    k = k or S.EVIDENCE_TOP_K
    sims = (line_vecs @ embed([skill]).T).ravel()
    return [lines[i] for i in np.argsort(-sims)[:k]]


def embedding_only_coverage(job_skills, cand_skills) -> float:
    """Required-skill coverage using embeddings alone (agreement signal for match_confidence)."""
    req = [s for s, i in job_skills if i == "required"]
    if not req or not cand_skills:
        return 0.0
    sims = embed(req) @ embed(cand_skills).T
    return float(np.mean(sims.max(axis=1) >= S.SKILL_SIM_AMBIG))
