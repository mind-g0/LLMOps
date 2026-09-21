import argparse
import json
import os
from pathlib import Path
from typing import Optional
 
from openai import OpenAI
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm
 
from dataset_utils import load_env_file
 
BASE = Path(__file__).parent.parent
load_env_file(BASE / ".env", BASE.parent / ".env")
EXTRACTION_MODEL = "gpt-4.1"  # verify current recommended model before a full run
RESUME_DATASETS = {"resume_dataset_hf", "synthetic_cv"}
 
 
class EducationEntry(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    gpa: Optional[str] = None
 
class ExperienceEntry(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
 
class ExtractedProfile(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
 
 
SYSTEM_PROMPT = (
    "Extract structured resume fields from the OCR text below. "
    "Only extract information that is actually present in the text -- "
    "if a field is not stated, leave it null or an empty list. "
    "Never guess, infer, or fill in a plausible-looking value for missing "
    "data; a null field is correct when the information genuinely isn't "
    "there, and is preferred over a fabricated guess."
)
 
 
@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=8))
def extract_one(client: OpenAI, ocr_text: str) -> ExtractedProfile:
    resp = client.responses.parse(
        model=EXTRACTION_MODEL,
        input=[{"role": "system", "content": SYSTEM_PROMPT},
               {"role": "user", "content": ocr_text}],
        text_format=ExtractedProfile,
    )
    return resp.output_parsed
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--pipeline", required=True, help="e.g. qwen3_vl, or qwen3_vl__control")
    ap.add_argument("--dataset", required=True, choices=sorted(RESUME_DATASETS))
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
 
    ocr_dir = BASE / "results" / "runs" / args.run_id / args.pipeline / args.dataset
    if not ocr_dir.exists():
        print(f"ERROR: {ocr_dir} not found — run run_pipeline.py for this pipeline/dataset first.")
        return
 
    docs = sorted(ocr_dir.glob("doc_*.md"))
    if args.limit:
        docs = docs[: args.limit]
 
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            f"OPENAI_API_KEY not found. Checked {BASE / '.env'} and {BASE.parent / '.env'} "
            f"(plus ENV_FILE if set)."
        )
    client = OpenAI(timeout=60.0)  # a stalled request now fails within 60s and retries/moves on,
                                     # instead of blocking indefinitely with no visible sign of progress
    n_ok = n_empty_input = n_failed = 0
 
    for doc_path in tqdm(docs, desc=f"extract_fields [{args.pipeline}/{args.dataset}]"):
        doc_id = doc_path.stem
        ocr_text = doc_path.read_text(encoding="utf-8")
        out_path = ocr_dir / f"{doc_id}_fields.json"
 
        if not ocr_text.strip():
            # Don't call the API on empty OCR output -- there's nothing to
            # extract, and doing so would just manufacture a hallucinated
            # profile from nothing. Record this explicitly as its own
            # extraction-method state rather than a null result.
            out_path.write_text(json.dumps(
                {"extraction_method": "skipped_empty_ocr_input", "fields": None}, indent=2))
            n_empty_input += 1
            continue
 
        try:
            profile = extract_one(client, ocr_text)
            out_path.write_text(json.dumps(
                {"extraction_method": "llm", "fields": profile.model_dump()},
                indent=2, ensure_ascii=False))
            n_ok += 1
        except Exception as e:
            out_path.write_text(json.dumps(
                {"extraction_method": "failed", "fields": None, "error": str(e)}, indent=2))
            n_failed += 1
 
    print(f"[{args.pipeline}/{args.dataset}] {n_ok} extracted, "
          f"{n_empty_input} skipped (empty OCR input), {n_failed} failed "
          f"-> {ocr_dir}")
 
 
if __name__ == "__main__":
    main()