import argparse
import json
import os
from pathlib import Path
 
from openai import OpenAI
 
from dataset_utils import load_env_file
from extract_fields import ExtractedProfile, extract_one
 
BASE = Path(__file__).parent.parent
GT_DIR = BASE / "data" / "ground_truth" / "resume_dataset_hf"
 
load_env_file(BASE / ".env", BASE.parent / ".env")
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
 
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            f"OPENAI_API_KEY not found. Checked {BASE / '.env'} and {BASE.parent / '.env'} "
            f"(plus ENV_FILE if set)."
        )
 
    client = OpenAI()
    gt_files = sorted(GT_DIR.glob("doc_*.json"))
    if not gt_files:
        print(f"No ground truth files found at {GT_DIR} -- run build_sample.py first.")
        return
    if args.limit:
        gt_files = gt_files[: args.limit]
 
    n_ok = n_skipped = n_failed = 0
    for gt_path in gt_files:
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        text = gt.get("ground_truth_text", "")
        if not text.strip():
            print(f"[{gt_path.stem}] SKIPPED -- no ground_truth_text to extract from")
            n_skipped += 1
            continue
        try:
            profile: ExtractedProfile = extract_one(client, text)
        except Exception as e:
            print(f"[{gt_path.stem}] WARNING: extraction failed: {e}")
            n_failed += 1
            continue
 
        gt["ground_truth_fields"] = {
            "name": profile.name or "",
            "email": profile.email or "",
            "phone": profile.phone or "",
            "skills": profile.skills,
            "education": [e.model_dump() for e in profile.education],
            "experience": [e.model_dump() for e in profile.experience],
        }
        gt["trust_level"] = "gold_via_gpt_extraction_from_clean_text"  # was "gold_skills_only" (noisy NER)
        gt_path.write_text(json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8")
        n_ok += 1
        print(f"[{gt_path.stem}] updated: {len(profile.skills)} skills, "
              f"{len(profile.education)} education, {len(profile.experience)} experience")
 
    print(f"\nDone: {n_ok} updated, {n_skipped} skipped (empty text), {n_failed} failed -> {GT_DIR}")
    print("Ground truth changed -- re-run compute_metrics.py to see the corrected skills-F1 "
          "(and NEW education/experience-accuracy numbers) for resume_dataset_hf.")
 
 
if __name__ == "__main__":
    main()