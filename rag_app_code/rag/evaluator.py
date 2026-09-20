import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
from openai import OpenAI
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=project_root / ".env", override=True)

api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "EMPTY"

openai_client = OpenAI(
    api_key=api_key,
    base_url=os.getenv("CUSTOM_API_BASE")
)

class EvaluationResult(BaseModel):
    match_score: float = Field(
        description="Calculated candidate match score between 0.0 and 100.0 using the strict weighted evaluation Rubric."
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Key candidate qualifications that explicitly match required JD items."
    )
    gaps: List[str] = Field(
        default_factory=list,
        description="Missing required skills, insufficient YOE, missing certifications, or missing degree level."
    )
    recommendation: str = Field(
        description="Final hiring decision summary. MUST start with 'Needs Human Review: [Reason]' ONLY IF logical inconsistencies, conflicting timelines, or unverified claims are detected. Otherwise, provide a standard clear recommendation."
    )

EVALUATION_SYSTEM_PROMPT = """
You are a highly analytical, strict HR Evaluator and Technical Talent Auditor.

YOUR OBJECTIVE:
Rigorously evaluate a candidate's CV against the target Job Description (JD). Calculate an objective, non-inflated `match_score` (0.0 - 100.0) based strictly on evidence in the CV.

SCORING RUBRIC (Total 100%):
1. Relevant Experience & YOE (Weight: 35%):
   - Match exact job functions, domain background, and required Years of Experience (YOE).
   - Deduct points heavily if total or relevant YOE is less than required in the JD.

2. Core Skills & Tech Stack (Weight: 30%):
   - Direct match between mandatory JD skills/tools and candidate skills.
   - Deduct points for missing core or mandatory technical tools.

3. Education & Academic Background (Weight: 20%):
   - Degree level match (e.g., Bachelor, Master) and field of study relevancy (e.g., Computer Science).
   - Deduct points if the degree is unrelated or below required level.

4. Projects, Certifications & Achievements (Weight: 15%):
   - Practical demonstration of skills via real-world projects, professional certs, or awards.
   - Deduct points if no practical projects or relevant certifications are provided.

HUMAN REVIEW CONDITION (CRITICAL):
Trigger "Needs Human Review: [Reason]" at the VERY BEGINNING of the `recommendation` field ONLY IF you detect logical anomalies or suspicious patterns in the CV, such as:
- Overlapping employment dates that create unrealistic YOE calculations.
- Claiming senior/advanced technical skills without any corresponding work experience or projects.
- Graduation years or employment history that logically contradict each other.
- Unusually high YOE claimed for a candidate with very sparse responsibility details.
- High experience claiming strong achievements, but completely lacking any verifiable project artifacts or work summary.

IF NO ANOMALIES/INCONSISTENCIES EXIST:
Do NOT include "Needs Human Review". Provide a standard, direct hiring recommendation (e.g., "Recommended for Interview", "Potentially Suitable", or "Strong Reject").

OUTPUT FORMAT:
Respond strictly with valid raw JSON matching the requested schema. No markdown code block wrappers (no ```json).
"""

def evaluate_candidate_against_jds(cv_text: str, matched_jds: list) -> EvaluationResult:
    """Evaluates candidate CV against top retrieved job description strictly."""
    top_jd = matched_jds[0] if matched_jds else {}
    jd_title = top_jd.get("title", "N/A")
    jd_reqs = top_jd.get("requirements", "N/A")

    prompt = f"""
TARGET JOB ROLE:
Title: {jd_title}
Requirements & Qualifications: {jd_reqs}

CANDIDATE PROFILE / EXTRACTION TEXT:
{cv_text}

Perform a strict weighted evaluation based on the Rubric (Experience 35%, Skills 30%, Education 20%, Projects/Certs 15%).
Compute an accurate match_score, identify explicit strengths & gaps, and provide a clear final recommendation.
Check carefully for any illogical data or timeline contradictions before deciding if 'Needs Human Review' is needed.
"""

    response = openai_client.beta.chat.completions.parse(
        model=os.getenv("CUSTOM_MODEL_NAME"),
        messages=[
            {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        response_format=EvaluationResult,
        temperature=0.0
    )
    return response.choices[0].message.parsed