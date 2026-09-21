import os
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=project_root / ".env", override=True)

api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "EMPTY"

openai_client = OpenAI(
    api_key=api_key,
    base_url=os.getenv("CUSTOM_API_BASE")
)

class WorkExperience(BaseModel):
    company_name: str = Field(description="Company name translated/transliterated into English")
    job_title_english: str = Field(description="Standardized English job title")
    start_year: Optional[int] = Field(default=None, description="Gregorian start year")
    end_year: Optional[int] = Field(default=None, description="Gregorian end year, or null if current")
    responsibilities_english: List[str] = Field(default_factory=list, description="List of core responsibilities translated into English")

class Education(BaseModel):
    degree_english: str = Field(description="Degree name translated into English")
    institution_english: str = Field(description="University or institution name translated into English")
    graduation_year: Optional[int] = Field(default=None, description="Gregorian graduation year")

class Project(BaseModel):
    project_name: str = Field(description="Project title in English")
    description_english: str = Field(description="Brief overview of the project in English")
    technologies_used: List[str] = Field(default_factory=list, description="List of tools or tech stack used")

class Certification(BaseModel):
    title_english: str = Field(description="Name of certification in English")
    issuing_organization: Optional[str] = Field(default=None, description="Organization issuing the certificate")
    issue_year: Optional[int] = Field(default=None, description="Gregorian issue year")

class CandidateCV(BaseModel):
    full_name_english: Optional[str] = Field(default=None, description="Candidate full name transliterated into English")
    location_english: Optional[str] = Field(default=None, description="City and country translated into English")
    email: Optional[str] = Field(default=None)
    phone: Optional[str] = Field(default=None)
    github_url: Optional[str] = Field(default=None, description="Candidate GitHub URL if present")
    linkedin_url: Optional[str] = Field(default=None, description="Candidate LinkedIn URL if present")
    portfolio_url: Optional[str] = Field(default=None, description="Candidate portfolio URL if present")
    total_years_experience: float = Field(default=0.0)
    skills_english: List[str] = Field(default_factory=list, description="Technical and professional skills translated into English")
    education_history: List[Education] = Field(default_factory=list, description="List of education records")
    experience_history: List[WorkExperience] = Field(default_factory=list, description="List of work experience records")
    projects: List[Project] = Field(default_factory=list, description="List of notable candidate projects")
    certifications: List[Certification] = Field(default_factory=list, description="List of earned certifications")
    experience_summary: str = Field(description="2-sentence concise summary of candidate technical background written strictly in English")
    languages_spoken: List[str] = Field(default_factory=list, description="Languages spoken by candidate, written in English")

SYSTEM_PROMPT = """
You are an expert HR data extraction engine specialized in multilingual resumes.

CRITICAL INSTRUCTIONS:
1. ALL extracted output values MUST be strictly in standard English, regardless of the input CV language.
2. Translate all job titles, responsibilities, degrees, institutions, cities, and countries into standard professional English.
3. Transliterate all candidate personal names accurately into standard Roman/English spelling.
4. Convert any Hijri dates into corresponding Gregorian calendar years.
5. Ensure the `experience_summary` field is written 100% in English prose without any foreign script.
6. Do NOT invent or hallucinate data. If a field is missing, output null or an empty list.

OUTPUT FORMAT REQUIREMENT:
You MUST respond strictly with a valid JSON object matching the requested schema.
Do NOT output markdown code blocks (no ```json wrappers). Output raw JSON only.
"""

def process_cv_single_pass(parsed_cv_text: str) -> CandidateCV:
    """Parses raw candidate CV text (Arabic or English) into standardized English Pydantic schema."""
    response = openai_client.beta.chat.completions.parse(
        model=os.getenv("CUSTOM_MODEL_NAME"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract candidate profile in English from the following CV text:\n\n{parsed_cv_text}"}
        ],
        response_format=CandidateCV,
        temperature=0.0
    )
    return response.choices[0].message.parsed

def extract_and_format_candidate_en(raw_cv_text: str) -> tuple:
    """Extracts CV data and returns both the raw data object and a formatted English string preview."""
    extracted_data = process_cv_single_pass(raw_cv_text)
    
    name = extracted_data.full_name_english or "N/A"
    location = extracted_data.location_english or "N/A"
    email = extracted_data.email or "N/A"
    phone = extracted_data.phone or "N/A"
    github = extracted_data.github_url or "N/A"
    linkedin = extracted_data.linkedin_url or "N/A"
    portfolio = extracted_data.portfolio_url or "N/A"

    skills = ", ".join(extracted_data.skills_english) if extracted_data.skills_english else "N/A"
    languages = ", ".join(extracted_data.languages_spoken) if extracted_data.languages_spoken else "N/A"

    edu_list = []
    for e in extracted_data.education_history:
        year_part = f" ({e.graduation_year})" if e.graduation_year else ""
        edu_list.append(f"- {e.degree_english} at {e.institution_english}{year_part}")
    education_str = "\n".join(edu_list) if edu_list else "None listed"

    exp_list = []
    for e in extracted_data.experience_history:
        start_val = e.start_year or "N/A"
        end_val = e.end_year or "Present"
        exp_list.append(f"- {e.job_title_english} at {e.company_name} ({start_val} - {end_val})")
    experience_str = "\n".join(exp_list) if exp_list else "None listed"

    proj_list = []
    for p in extracted_data.projects:
        tech_part = f" [Tech: {', '.join(p.technologies_used)}]" if p.technologies_used else ""
        proj_list.append(f"- {p.project_name}: {p.description_english}{tech_part}")
    
    # Clearly highlight missing projects
    projects_str = "\n".join(proj_list) if proj_list else "None listed (Needs Review)"

    cert_list = []
    for c in extracted_data.certifications:
        org_part = f" from {c.issuing_organization}" if c.issuing_organization else ""
        year_part = f" ({c.issue_year})" if c.issue_year else ""
        cert_list.append(f"- {c.title_english}{org_part}{year_part}")
    certs_str = "\n".join(cert_list) if cert_list else "None listed"

    summary = extracted_data.experience_summary or "No summary available."

    english_preview = (
        f"Name: {name}\n"
        f"Location: {location}\n"
        f"Contact: {email} | {phone}\n"
        f"Links:\n"
        f"  - GitHub: {github}\n"
        f"  - LinkedIn: {linkedin}\n"
        f"  - Portfolio: {portfolio}\n"
        f"Languages: {languages}\n"
        f"Skills: {skills}\n\n"
        f"Education:\n{education_str}\n\n"
        f"Experience ({extracted_data.total_years_experience} YOE):\n{experience_str}\n\n"
        f"Projects:\n{projects_str}\n\n"
        f"Certifications:\n{certs_str}\n\n"
        f"Summary:\n{summary}"
    )

    return extracted_data, english_preview