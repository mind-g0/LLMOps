import os
from pydantic import BaseModel, Field
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(
    api_key=os.getenv("LLM_API_KEY", "EMPTY"),
    base_url=os.getenv("CUSTOM_API_BASE")
)

class WorkExperience(BaseModel):
    company_name: str
    job_title_english: str
    start_year: Optional[int] = Field(default=None, description="Gregorian start year")
    end_year: Optional[int] = Field(default=None, description="Gregorian end year, or null if current")
    responsibilities_english: List[str]

class CandidateCV(BaseModel):
    full_name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    total_years_experience: float
    skills_english: List[str]
    experience_history: List[WorkExperience]
    experience_summary: str = Field(description="2-sentence summary of candidate technical background in English")
    languages_spoken: List[str] = Field(description="Languages identified from CV (e.g. ['English', 'Arabic'])")

SYSTEM_PROMPT = """
You are an expert HR evaluation engine specialized in bilingual (Arabic/English) resume extraction.

CRITICAL INSTRUCTIONS:
1. ALL output string fields MUST be in standard English.
2. Translate all Arabic job titles, duties, and degrees into standard HR English terms.
3. Keep original proper nouns (company names, universities) as recognized international English spelling or transliterate them accurately.
4. Convert any Hijri dates (e.g., 1442 AH) to corresponding Gregorian years.
5. Do NOT invent data. If a field is missing, set it to null or empty list.
"""

def process_cv_single_pass(parsed_cv_text: str) -> CandidateCV:
    """Extracts Arabic/English CV text into standardized English Pydantic schema."""
    response = openai_client.beta.chat.completions.parse(
        model=os.getenv("CUSTOM_MODEL_NAME"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Parse the following CV text:\n\n{parsed_cv_text}"}
        ],
        response_format=CandidateCV,
        temperature=0.0
    )
    return response.choices[0].message.parsed