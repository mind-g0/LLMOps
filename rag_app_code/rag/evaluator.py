import os
from typing import List
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("LLM_API_KEY", "EMPTY"),
    base_url=os.getenv("CUSTOM_API_BASE")
)

class CandidateEvaluation(BaseModel):
    match_score: float = Field(description="Match score from 0.0 to 100.0")
    strengths: List[str] = Field(description="Key strengths matching job requirements")
    gaps: List[str] = Field(description="Missing skills or experience gaps relative to requirements")
    recommendation: str = Field(description="Final hiring recommendation summary and rationale")

SYSTEM_EVALUATOR_PROMPT = """
You are an expert HR ATS evaluation engine.
Compare the candidate's CV against the retrieved job requirements in an objective, precise manner.
Provide an objective match score (0-100), key candidate strengths, skill/experience gaps, and a clear hiring recommendation.
"""

def evaluate_candidate_against_jds(cv_text: str, matched_jds: list) -> CandidateEvaluation:
    if not matched_jds:
        return CandidateEvaluation(
            match_score=0.0,
            strengths=[],
            gaps=["No matching job descriptions found in vector store."],
            recommendation="Do not proceed due to lack of matching job descriptions."
        )

    top_jd = matched_jds[0]

    user_prompt = f"""
Candidate CV Content:
{cv_text}

Target Job Requirements:
Title: {top_jd.get('title', 'N/A')}
Details: {top_jd.get('summary_text', top_jd.get('description', 'N/A'))}
    """

    response = client.beta.chat.completions.parse(
        model=os.getenv("CUSTOM_MODEL_NAME"),
        messages=[
            {"role": "system", "content": SYSTEM_EVALUATOR_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format=CandidateEvaluation,
        temperature=0.0
    )

    return response.choices[0].message.parsed