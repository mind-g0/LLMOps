import os
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

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

    # 1. Force reload of .env file from possible locations
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    
    if (parent_dir / ".env").exists():
        load_dotenv(dotenv_path=parent_dir / ".env", override=True)
    elif (current_dir / ".env").exists():
        load_dotenv(dotenv_path=current_dir / ".env", override=True)
    else:
        load_dotenv(override=True)

    # 2. Extract environment variables with safe defaults
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "EMPTY"
    base_url = os.getenv("CUSTOM_API_BASE")
    model_name = os.getenv("CUSTOM_MODEL_NAME")

    # Debug print to confirm what credentials are being used
    print(f"Connecting to LLM Server: {base_url} | Model: {model_name} | Key: {api_key[:5]}***")

    # 3. Instantiate client dynamically
    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )

    top_jd = matched_jds[0]

    user_prompt = f"""
Candidate CV Content:
{cv_text}

Target Job Requirements:
Title: {top_jd.get('title', 'N/A')}
Details: {top_jd.get('description', top_jd.get('summary_text', 'N/A'))}
    """

    response = client.beta.chat.completions.parse(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_EVALUATOR_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format=CandidateEvaluation,
        temperature=0.0
    )

    return response.choices[0].message.parsed