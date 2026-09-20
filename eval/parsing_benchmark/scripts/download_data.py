import json
import re
import shutil
import zipfile
from pathlib import Path
 
import kagglehub
from huggingface_hub import hf_hub_download
 
BASE = Path(__file__).parent.parent
RAW_DIR = BASE / "data" / "raw"
 
KAGGLE_DATASETS = {
    # local_name: kaggle_id
    "resume_dataset_labeled": "snehaanbhawal/resume-dataset",  
}
 
MEHYAAR_REPO = "Mehyaar/Annotated_NER_PDF_Resumes"  
MEHYAAR_ZIP_FILENAME = "ResumesPDF.zip"
MEHYAAR_ANNOTATIONS_ZIP = "ResumesJsonAnnotated.zip"  # separate file, NOT reachable via load_dataset()
 
 
def download_kaggle_dataset(local_name: str, kaggle_id: str) -> None:
    dest = RAW_DIR / local_name
    if dest.exists() and any(dest.iterdir()):
        print(f"[skip] {local_name} already present at {dest}")
        return
    print(f"[download] {kaggle_id} (Kaggle) ...")
    cache_path = Path(kagglehub.dataset_download(kaggle_id))
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cache_path, dest, dirs_exist_ok=True)
    print(f"[done] {local_name} -> {dest}")
 
 
def _sanitize_unicode(obj):
    """Some Mehyaar annotation JSONs contain unpaired surrogate codepoints
    (garbled emoji, likely from an upstream scrape/export step) that raise
    UnicodeEncodeError the moment you try to write them back out as UTF-8.
    Recursively replace anything unencodable with U+FFFD rather than crash
    or silently drop the whole record -- the rest of the text stays intact."""
    if isinstance(obj, str):
        return obj.encode("utf-8", errors="replace").decode("utf-8")
    if isinstance(obj, dict):
        return {k: _sanitize_unicode(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_unicode(v) for v in obj]
    return obj
 
 
def extract_index(name: str) -> str | None:
    m = re.search(r"\((\d+)\)", name)
    return m.group(1) if m else None
 
 
def download_mehyaar() -> None:
    """Mehyaar's repo has TWO separate zip files, confirmed by inspecting
    the dataset viewer's own error message for this repo:
      - ResumesPDF.zip           -- the PDFs
      - ResumesJsonAnnotated.zip -- one {"text", "annotations"} JSON per CV
    load_dataset(repo_id) does NOT combine these -- it auto-discovers only
    the PDF zip as a single generic 'pdf' column and knows nothing about
    the annotations zip, then errors trying to decode PDFs through a
    feature-type decoder that expects a source_url the local cache doesn't
    have. Read both zips directly instead; don't go through load_dataset()
    for this dataset at all.
 
    Matching: each JSON is named like "cv (12)_annotated.json" and each PDF
    like "cv (12).pdf" -- the "(N)" index is what ties them together. Pull
    that index out explicitly and match on it, rather than assuming the
    two independently-packed zips share any ordering.
    """
    local_name = "resume_dataset_hf"
    dest = RAW_DIR / local_name
    manifest_path = dest / "manifest.jsonl"
    if manifest_path.exists():
        print(f"[skip] {local_name} already present at {dest}")
        return
    dest.mkdir(parents=True, exist_ok=True)
 
    print(f"[download] ResumesPDF.zip (Hugging Face, dataset repo file) ...")
    pdf_zip_path = Path(hf_hub_download(
        repo_id=MEHYAAR_REPO, repo_type="dataset", filename=MEHYAAR_ZIP_FILENAME))
    pdf_dir = dest / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(pdf_zip_path) as zf:
        pdf_members = [m for m in zf.namelist() if m.lower().endswith(".pdf")]
        zf.extractall(pdf_dir, members=pdf_members)
    pdf_files = sorted(pdf_dir.rglob("*.pdf"))
    print(f"[{local_name}] extracted {len(pdf_files)} PDFs from {MEHYAAR_ZIP_FILENAME}")
 
    print(f"[download] {MEHYAAR_ANNOTATIONS_ZIP} (Hugging Face, dataset repo file) ...")
    json_zip_path = Path(hf_hub_download(
        repo_id=MEHYAAR_REPO, repo_type="dataset", filename=MEHYAAR_ANNOTATIONS_ZIP))
    json_dir = dest / "annotations"
    json_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(json_zip_path) as zf:
        json_members = [m for m in zf.namelist() if m.lower().endswith(".json")]
        zf.extractall(json_dir, members=json_members)
    json_files = sorted(json_dir.rglob("*.json"))
    print(f"[{local_name}] extracted {len(json_files)} annotation files from {MEHYAAR_ANNOTATIONS_ZIP}")
 
    pdf_by_index = {}
    for p in pdf_files:
        idx = extract_index(p.stem)
        if idx:
            pdf_by_index[idx] = p
 
    rows, n_matched, n = [], 0, 0
    for json_path in json_files:
        idx = extract_index(json_path.stem)
        matched_pdf = pdf_by_index.get(idx) if idx else None
        try:
            record = json.loads(json_path.read_text(encoding="utf-8", errors="replace"))
            record = _sanitize_unicode(record)
        except json.JSONDecodeError as e:
            print(f"[{local_name}] WARNING: could not parse {json_path.name}: {e} — skipping.")
            continue
 
        rows.append({
            "row_index": n,
            "pdf_path": str(matched_pdf.relative_to(dest)) if matched_pdf else None,
            "match_method": "index" if matched_pdf else "unmatched",
            "text": record.get("text", ""),
            "annotations": record.get("annotations", []),
        })
        n_matched += int(matched_pdf is not None)
        n += 1
 
    with open(manifest_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
 
    print(f"[done] {local_name} -> {dest} ({n} records, {n_matched} matched to a PDF by index, "
          f"{n - n_matched} unmatched)")
    if n_matched < n:
        print(f"[{local_name}] WARNING: {n - n_matched} record(s) had no matching PDF by index "
              f"-- inspect filename patterns in {json_dir} vs {pdf_dir} if this count is large; "
              f"build_sample.py already drops any record with pdf_path=None, so this just means "
              f"fewer usable docs than {n}, not silently wrong ones.")
    if json_files:
        sample = json.loads(json_files[0].read_text(encoding="utf-8"))
        print(f"[{local_name}] sample record keys: {list(sample.keys())} -- "
              f"verify 'annotations' actually looks like what parse_skills_from_annotations() "
              f"in build_sample.py expects before trusting the skills-F1 numbers.")
 
 
def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for local_name, kaggle_id in KAGGLE_DATASETS.items():
        download_kaggle_dataset(local_name, kaggle_id)
    download_mehyaar()
 
 
if __name__ == "__main__":
    main()