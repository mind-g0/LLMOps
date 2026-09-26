import argparse
import csv
import json
import random
import shutil
from pathlib import Path
 
BASE = Path(__file__).parent.parent
RAW_DIR = BASE / "data" / "raw"
SAMPLE_ROOT = BASE / "data" / "samples"
GT_ROOT = BASE / "data" / "ground_truth"
SEED = 42
 
DEV_FRACTION = {
    "resume_dataset_hf": 0.2,
    "synthetic_cv": 0.2,
}
 
EMPTY_FIELDS = {"name": "", "email": "", "phone": "", "skills": [],
                "experience_years": None, "education": [], "experience": []}
 
 
def assign_splits(doc_ids: list[str], dev_fraction: float, seed: int = SEED) -> dict[str, str]:
    ids = doc_ids[:]
    random.Random(seed).shuffle(ids)
    n_dev = round(len(ids) * dev_fraction)
    return {doc_id: ("dev" if i < n_dev else "test") for i, doc_id in enumerate(ids)}
 
 
def write_gt(gt_dir: Path, doc_id: str, record: dict):
    gt_dir.mkdir(parents=True, exist_ok=True)
    (gt_dir / f"{doc_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
 
 
# --- 1. resume_dataset_hf / Mehyaar (English, GOLD skills only) ------------
 
def parse_skills_from_annotations(annotations) -> list[str] | None:
    """Best-effort parser for Mehyaar's NER span format. Confirmed against a
    real record: entity text comes prefixed with the label itself, e.g.
    {"label": "SKILL", "text": "SKILL: Box"} -- the prefix is a formatting
    artifact of however this was exported, not part of the actual skill
    name, and left in place it silently tanks every fuzzy-match comparison
    downstream even for genuinely correct pairs. Strip it here.
 
    Separately -- confirmed by inspecting real output -- a large share of
    tagged "SKILL" entities in this dataset are not skills at all (personal
    details, contact-info fragments, generic nouns like "Box"/"MS"/"COM").
    This looks like an over-inclusive auto-tagger, not curated human
    labeling, despite the dataset's reputation. Stripping the prefix fixes
    the string-matching bug; it does NOT fix noisy ground truth, and
    skills-F1 against this dataset should be reported as bounded by that
    noise, not read as a clean measure of extraction quality on its own."""
    if not annotations:
        return []
    def strip_label_prefix(text: str, label: str) -> str:
        prefix = f"{label}: "
        return text[len(prefix):] if text.upper().startswith(prefix.upper()) else text
    try:
        if isinstance(annotations[0], dict) and "label" in annotations[0]:
            return sorted({strip_label_prefix(a["text"], a["label"]) for a in annotations
                           if a.get("label", "").upper() in ("SKILL", "SKILLS", "TECH_SKILL")})
        if isinstance(annotations[0], (list, tuple)) and len(annotations[0]) >= 3:
            return sorted({strip_label_prefix(a[-1], str(a[2])) for a in annotations
                           if str(a[2]).upper().startswith("SKILL")})
    except (KeyError, IndexError, TypeError):
        pass
    return None
 
 
def build_mehyaar(n: int):
    name = "resume_dataset_hf"
    raw_dir, sample_dir, gt_dir = RAW_DIR / name, SAMPLE_ROOT / name, GT_ROOT / name
    manifest_path = raw_dir / "manifest.jsonl"
    if not manifest_path.exists():
        print(f"[{name}] WARNING: {manifest_path} not found — run download_data.py first.")
        return
 
    records = [json.loads(line) for line in open(manifest_path, encoding="utf-8")]
    records = [r for r in records if r.get("pdf_path")]  # never fabricate a PDF path
    if n > len(records):
        print(f"[{name}] WARNING: requested {n} but only {len(records)} have a matched PDF — using all.")
    random.Random(SEED).shuffle(records)
    records = records[:n]
 
    sample_dir.mkdir(parents=True, exist_ok=True)
    doc_ids = [f"doc_{i:04d}" for i in range(1, len(records) + 1)]
    splits = assign_splits(doc_ids, DEV_FRACTION[name])
 
    n_unparsed = 0
    for doc_id, record in zip(doc_ids, records):
        shutil.copy2(raw_dir / record["pdf_path"], sample_dir / f"{doc_id}.pdf")
        skills = parse_skills_from_annotations(record.get("annotations"))
        needs_review = skills is None
        n_unparsed += int(needs_review)
 
        fields = dict(EMPTY_FIELDS)
        fields["skills"] = skills or []
        write_gt(gt_dir, doc_id, {
            "doc_id": doc_id, "source_dataset": name, "split": splits[doc_id],
            "detected_language": "en", "is_scanned_image": False,
            "ground_truth_text": record.get("text", ""),
            "ground_truth_fields": fields,
            "trust_level": "gold_skills_only",  
            "match_method": record.get("match_method", "unknown"),
            "needs_human_review": needs_review,
        })
    print(f"[{name}] wrote {len(records)} docs "
          f"({sum(v=='dev' for v in splits.values())} dev / {sum(v=='test' for v in splits.values())} test)")
    if n_unparsed:
        print(f"[{name}] WARNING: {n_unparsed} doc(s) had unparseable annotations — "
              f"skills GT left empty and needs_human_review=true. Inspect the actual "
              f"annotation schema in manifest.jsonl and fix parse_skills_from_annotations() "
              f"before trusting the skills-F1 numbers for this dataset.")
 
 
# --- 2. synthetic_cv (bilingual, GOLD everything) --------------------------
 
def build_synthetic(n: int):
    name = "synthetic_cv"
    raw_dir, sample_dir, gt_dir = RAW_DIR / name, SAMPLE_ROOT / name, GT_ROOT / name
    manifest_path = raw_dir / "manifest.jsonl"
    if not manifest_path.exists():
        print(f"[{name}] WARNING: {manifest_path} not found — run generate_synthetic_cvs.py first.")
        return
 
    records = [json.loads(line) for line in open(manifest_path, encoding="utf-8")]
    if n > len(records):
        print(f"[{name}] WARNING: requested {n} but only {len(records)} were generated — using all.")
    records = records[:n]  # already in generation order; no reason to reshuffle a synthetic set
 
    sample_dir.mkdir(parents=True, exist_ok=True)
    doc_ids = [r["doc_id"] for r in records]
    splits = assign_splits(doc_ids, DEV_FRACTION[name])
 
    for record in records:
        doc_id = record["doc_id"]
        shutil.copy2(raw_dir / f"{doc_id}.pdf", sample_dir / f"{doc_id}.pdf")
        gt = record["ground_truth"]
        write_gt(gt_dir, doc_id, {
            "doc_id": doc_id, "source_dataset": name, "split": splits[doc_id],
            "detected_language": gt["language"], "is_scanned_image": False,
            "ground_truth_text": record.get("ground_truth_text"),  # per-template reading-order text, from cv_gen.py
            "ground_truth_fields": {
                "name": gt["name"], "email": gt["email"], "phone": gt["phone"],
                "skills": gt["skills"], "education": gt["education"],
                "experience": gt["experience"],
            },
            "template": record["template"], "role": record["role"],
            "trust_level": "gold", "needs_human_review": False,
        })
    n_ar = sum(1 for r in records if r["ground_truth"]["language"] == "ar")
    print(f"[{name}] wrote {len(records)} docs ({n_ar} ar / {len(records) - n_ar} en) "
          f"({sum(v=='dev' for v in splits.values())} dev / {sum(v=='test' for v in splits.values())} test)")
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    args = ap.parse_args()
    build_mehyaar(args.n)
    build_synthetic(args.n)
    print("\nDone. Every ground_truth/*.json now has a 'split' field (dev/test) — "
          "iterate against dev/, report only on test/.")
 
 
if __name__ == "__main__":
    main()