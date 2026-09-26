import argparse
import os
import json
import random
from difflib import SequenceMatcher
from pathlib import Path
from typing import Literal, Optional
 
from jinja2 import Template
from openai import OpenAI
from pydantic import BaseModel, Field
from weasyprint import HTML
 
from dataset_utils import load_env_file
 
BASE = Path(__file__).parent.parent
load_env_file(BASE / ".env", BASE.parent / ".env")
 
OUT_RAW = BASE / "data" / "raw" / "synthetic_cv"
MODEL = "gpt-4.1"  
SEED = 42
 
LANGUAGE_PLAN = {"ar": 0.5, "en": 0.5}  # must sum to 1.0; add "mixed": x if wanted
 
ROLE_POOL = ["Data Scientist", "Backend Engineer", "HR Business Partner",
             "Financial Analyst", "Civil Engineer", "Marketing Manager",
             "Registered Nurse", "Supply Chain Analyst", "UX Designer",
             "Mechanical Engineer", "Recruiter", "Sales Executive"]
SENIORITY_POOL = ["entry-level", "mid-level", "senior", "lead"]
INDUSTRY_POOL = ["fintech", "healthcare", "logistics", "e-commerce",
                  "manufacturing", "telecom", "education", "government"]
REGION_POOL_AR = ["Riyadh, Saudi Arabia", "Cairo, Egypt", "Amman, Jordan",
                   "Dubai, UAE", "Rabat, Morocco"]
REGION_POOL_EN = ["Riyadh, Saudi Arabia", "Cairo, Egypt", "London, UK",
                   "Toronto, Canada", "Austin, USA"]
TEMPLATE_POOL = ["single_column", "two_column_sidebar", "table_header"]
 
 
# ---------------------------------------------------------------------------
# Schema — this IS the ground truth once rendered. Keep it aligned with your
# CandidateProfile/education/experience schemas from the main project.
# ---------------------------------------------------------------------------
 
class EducationEntry(BaseModel):
    degree: str
    institution: str
    start_year: int
    end_year: int
    gpa: Optional[str] = None
 
class ExperienceEntry(BaseModel):
    company: str
    role: str
    start_date: str  # "Mon YYYY"
    end_date: str    # "Mon YYYY" or "Present"
    description: str
 
class SyntheticCV(BaseModel):
    language: Literal["ar", "en"]
    name: str
    email: str
    phone: str
    location: str
    summary: str
    skills: list[str] = Field(min_length=6, max_length=20)
    education: list[EducationEntry] = Field(min_length=1, max_length=2)
    experience: list[ExperienceEntry] = Field(min_length=1, max_length=4)
 
 
SYSTEM_PROMPT = (
    "You generate realistic, entirely fictional resume content for a "
    "document-parsing benchmark. Every person, company and detail must be "
    "invented -- never reuse a real person's identity. Write naturally, as "
    "a real professional would write about themselves, in the requested "
    "language. Return ONLY the structured fields requested."
)
 
 
def build_user_prompt(role, seniority, industry, region, language) -> str:
    lang_name = "Arabic" if language == "ar" else "English"
    return (
        f"Generate one fictional candidate profile for a {seniority} "
        f"{role} in the {industry} industry, based in {region}. "
        f"Write all narrative fields (summary, experience descriptions) in "
        f"{lang_name}. Names, company names and institution names should be "
        f"plausible for the given region and written in {lang_name} script. "
        f"Vary sentence structure and vocabulary from what you might have "
        f"generated before -- avoid stock phrasing."
    )
 
 
def generate_one(client: OpenAI, role, seniority, industry, region, language) -> SyntheticCV:
    resp = client.responses.parse(
        model=MODEL,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(role, seniority, industry, region, language)},
        ],
        text_format=SyntheticCV,
    )
    return resp.output_parsed
 
 
def check_near_duplicates(profiles: list[SyntheticCV], threshold: float = 0.85) -> list[tuple[int, int, float]]:
    """Cheap pairwise summary-text similarity check. Flags pairs for manual
    review -- does not auto-drop, since a false positive here just costs a
    look, but auto-dropping could silently shrink your sample below target."""
    flagged = []
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            ratio = SequenceMatcher(None, profiles[i].summary, profiles[j].summary).ratio()
            if ratio >= threshold:
                flagged.append((i, j, ratio))
    return flagged
 
 
# ---------------------------------------------------------------------------
# Rendering — deterministic, no LLM involved. The ground truth is the
# SyntheticCV object; this just lays it out on a page.
# ---------------------------------------------------------------------------
 
TEMPLATES = {
    "single_column": Template("""
    <html><body style="font-family: 'Noto Sans Arabic', 'Noto Sans', sans-serif;
                        direction: {{ 'rtl' if cv.language == 'ar' else 'ltr' }};">
      <h1>{{ cv.name }}</h1>
      <p>{{ cv.email }} | {{ cv.phone }} | {{ cv.location }}</p>
      <h2>{{ 'الملخص' if cv.language == 'ar' else 'Summary' }}</h2>
      <p>{{ cv.summary }}</p>
      <h2>{{ 'المهارات' if cv.language == 'ar' else 'Skills' }}</h2>
      <p>{{ cv.skills | join(', ') }}</p>
      <h2>{{ 'الخبرة' if cv.language == 'ar' else 'Experience' }}</h2>
      {% for e in cv.experience %}
        <p><b>{{ e.role }}</b> — {{ e.company }} ({{ e.start_date }} - {{ e.end_date }})<br>{{ e.description }}</p>
      {% endfor %}
      <h2>{{ 'التعليم' if cv.language == 'ar' else 'Education' }}</h2>
      {% for ed in cv.education %}
        <p>{{ ed.degree }}, {{ ed.institution }} ({{ ed.start_year }}-{{ ed.end_year }}){% if ed.gpa %} — GPA {{ ed.gpa }}{% endif %}</p>
      {% endfor %}
    </body></html>"""),
 
    "two_column_sidebar": Template("""
    <html><body style="font-family: 'Noto Sans Arabic', 'Noto Sans', sans-serif;
                        direction: {{ 'rtl' if cv.language == 'ar' else 'ltr' }};">
      <table width="100%"><tr>
        <td width="30%" style="vertical-align: top; background:#eee; padding:10px;">
          <h2>{{ cv.name }}</h2>
          <p>{{ cv.email }}<br>{{ cv.phone }}<br>{{ cv.location }}</p>
          <h3>{{ 'المهارات' if cv.language == 'ar' else 'Skills' }}</h3>
          <ul>{% for s in cv.skills %}<li>{{ s }}</li>{% endfor %}</ul>
          <h3>{{ 'التعليم' if cv.language == 'ar' else 'Education' }}</h3>
          {% for ed in cv.education %}<p>{{ ed.degree }}<br>{{ ed.institution }}<br>{{ ed.start_year }}-{{ ed.end_year }}</p>{% endfor %}
        </td>
        <td style="vertical-align: top; padding:10px;">
          <h2>{{ 'الملخص' if cv.language == 'ar' else 'Summary' }}</h2>
          <p>{{ cv.summary }}</p>
          <h2>{{ 'الخبرة' if cv.language == 'ar' else 'Experience' }}</h2>
          {% for e in cv.experience %}<p><b>{{ e.role }}</b> — {{ e.company }} ({{ e.start_date }} - {{ e.end_date }})<br>{{ e.description }}</p>{% endfor %}
        </td>
      </tr></table>
    </body></html>"""),
 
    "table_header": Template("""
    <html><body style="font-family: 'Noto Sans Arabic', 'Noto Sans', sans-serif;
                        direction: {{ 'rtl' if cv.language == 'ar' else 'ltr' }};">
      <table width="100%" style="border-bottom:2px solid #333;"><tr>
        <td><h1>{{ cv.name }}</h1></td>
        <td align="right">{{ cv.email }}<br>{{ cv.phone }}<br>{{ cv.location }}</td>
      </tr></table>
      <h2>{{ 'الملخص' if cv.language == 'ar' else 'Summary' }}</h2><p>{{ cv.summary }}</p>
      <h2>{{ 'الخبرة' if cv.language == 'ar' else 'Experience' }}</h2>
      {% for e in cv.experience %}<p><b>{{ e.role }}</b>, {{ e.company }} ({{ e.start_date }}-{{ e.end_date }})<br>{{ e.description }}</p>{% endfor %}
      <h2>{{ 'التعليم' if cv.language == 'ar' else 'Education' }}</h2>
      {% for ed in cv.education %}<p>{{ ed.degree }}, {{ ed.institution }}, {{ ed.start_year }}-{{ ed.end_year }}</p>{% endfor %}
      <h2>{{ 'المهارات' if cv.language == 'ar' else 'Skills' }}</h2><p>{{ cv.skills | join(' • ') }}</p>
    </body></html>"""),
}
 
 
def render_canonical_text(cv: SyntheticCV, template_name: str) -> str:
    """Plain-text reading-order transcription matching what THIS SPECIFIC
    template actually lays out on the page -- not a generic order. CER
    against a single fixed order regardless of visual layout would inflate
    error for correct OCR that (correctly) read a sidebar-then-main-column
    or table-header layout in its own natural order. Each branch below
    mirrors its matching entry in TEMPLATES exactly: same fields, same
    section order, same section-header language (EN/AR) as what's
    physically printed on the page."""
    ar = cv.language == "ar"
    L = {
        "summary": "الملخص" if ar else "Summary", "skills": "المهارات" if ar else "Skills",
        "experience": "الخبرة" if ar else "Experience", "education": "التعليم" if ar else "Education",
    }
    exp_lines = [f"{e.role} — {e.company} ({e.start_date} - {e.end_date})\n{e.description}"
                 for e in cv.experience]
    edu_lines_full = [f"{e.degree}, {e.institution} ({e.start_year}-{e.end_year})"
                       + (f" — GPA {e.gpa}" if e.gpa else "") for e in cv.education]
    edu_lines_short = [f"{e.degree}\n{e.institution}\n{e.start_year}-{e.end_year}" for e in cv.education]
 
    if template_name == "single_column":
        parts = [cv.name, f"{cv.email} | {cv.phone} | {cv.location}",
                  L["summary"], cv.summary, L["skills"], ", ".join(cv.skills),
                  L["experience"], *exp_lines, L["education"], *edu_lines_full]
    elif template_name == "two_column_sidebar":
        # Sidebar column fully, then main column -- matches RESUME_MULTICOL_PROMPT's
        # own instruction ("transcribe each column completely ... before moving on"),
        # so a correctly-following OCR is scored fairly against this order.
        parts = [cv.name, cv.email, cv.phone, cv.location,
                  L["skills"], *cv.skills, L["education"], *edu_lines_short,
                  L["summary"], cv.summary, L["experience"], *exp_lines]
    elif template_name == "table_header":
        parts = [cv.name, f"{cv.email} {cv.phone} {cv.location}",
                  L["summary"], cv.summary, L["experience"],
                  *[f"{e.role}, {e.company} ({e.start_date}-{e.end_date})\n{e.description}" for e in cv.experience],
                  L["education"],
                  *[f"{e.degree}, {e.institution}, {e.start_year}-{e.end_year}" for e in cv.education],
                  L["skills"], " • ".join(cv.skills)]
    else:
        raise ValueError(f"No canonical-text renderer for template {template_name!r}")
    return "\n".join(parts)
 
 
def render_pdf(cv: SyntheticCV, template_name: str, out_path: Path):
    html = TEMPLATES[template_name].render(cv=cv)
    HTML(string=html).write_pdf(str(out_path))
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    args = ap.parse_args()
 
    assert abs(sum(LANGUAGE_PLAN.values()) - 1.0) < 1e-6, "LANGUAGE_PLAN must sum to 1.0"
 
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            f"OPENAI_API_KEY not found. Checked {BASE / '.env'} and {BASE.parent / '.env'} "
            f"(plus ENV_FILE if set).\n"
            f"Check: (1) the file is literally named '.env' (not '.env.txt'), "
            f"(2) it has a line reading exactly OPENAI_API_KEY=sk-... with no quotes and "
            f"no spaces around '=', or (3) set ENV_FILE=/exact/path/.env explicitly."
        )
    client = OpenAI()  # reads OPENAI_API_KEY from env
    rng = random.Random(SEED)
 
    languages = []
    for lang, frac in LANGUAGE_PLAN.items():
        languages += [lang] * round(frac * args.n)
    languages = (languages + ["en"] * args.n)[:args.n]
    rng.shuffle(languages)
 
    profiles, manifest = [], []
    for i, language in enumerate(languages, start=1):
        role = rng.choice(ROLE_POOL)
        seniority = rng.choice(SENIORITY_POOL)
        industry = rng.choice(INDUSTRY_POOL)
        region = rng.choice(REGION_POOL_AR if language == "ar" else REGION_POOL_EN)
        template_name = rng.choice(TEMPLATE_POOL)
 
        try:
            cv = generate_one(client, role, seniority, industry, region, language)
        except Exception as e:
            print(f"[{i}/{args.n}] GENERATION FAILED ({role}/{language}): {e}")
            continue
 
        doc_id = f"doc_{i:04d}"
        pdf_path = OUT_RAW / f"{doc_id}.pdf"
        render_pdf(cv, template_name, pdf_path)
        canonical_text = render_canonical_text(cv, template_name)
 
        profiles.append(cv)
        manifest.append({
            "doc_id": doc_id, "template": template_name, "role": role,
            "seniority": seniority, "industry": industry, "region": region,
            "language": language, "ground_truth": cv.model_dump(),
            "ground_truth_text": canonical_text,
        })
        print(f"[{i}/{args.n}] {doc_id}: {language} {seniority} {role} ({template_name})")
 
    dup_pairs = check_near_duplicates(profiles)
    if dup_pairs:
        print(f"\nWARNING: {len(dup_pairs)} near-duplicate summary pair(s) found "
              f"(similarity >= 0.85) — review before treating the batch as fully diverse:")
        for i, j, ratio in dup_pairs[:10]:
            print(f"  doc_{i+1:04d} <-> doc_{j+1:04d}: {ratio:.2f}")
 
    with open(OUT_RAW / "manifest.jsonl", "w", encoding="utf-8") as f:
        for row in manifest:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
 
    print(f"\nDone. {len(manifest)}/{args.n} CVs generated -> {OUT_RAW}")
    print("Ground truth for every field is in manifest.jsonl — exact by construction, "
          "no re-extraction or human labeling needed for this dataset.")
 
 
if __name__ == "__main__":
    main()