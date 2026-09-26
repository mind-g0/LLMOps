import argparse
import json
import time
from pathlib import Path
 
from tqdm import tqdm
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
 
from dataset_utils import iter_dataset_samples, get_run_id, write_run_manifest
 
BASE = Path(__file__).parent.parent
SAMPLE_ROOT = BASE / "data" / "samples"
 
 
def build_converter(mode: str) -> DocumentConverter:
    if mode == "full":
        return DocumentConverter()  # library defaults: OCR + table structure + DocLayNet layout model
    if mode == "simple":
        # Text-layer only: no OCR, no table-structure model, no layout
        # reconstruction beyond the raw text stream. Isolates whether
        # DocLayNet's reading-order reconstruction (or markdown formatting
        # from export_to_markdown) is what's adding error on digital-native
        # PDFs, vs. genuine content loss.
        opts = PdfPipelineOptions(do_ocr=False, do_table_structure=False)
        return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    raise ValueError(f"mode must be 'full' or 'simple', got {mode!r}")
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--mode", choices=["full", "simple"], default="simple",
                     help="'full' = library defaults (OCR + table structure + DocLayNet layout model). "
                          "'simple' = text-layer only, no OCR, no table model -- use this to test whether "
                          "the full pipeline's layout reconstruction/markdown formatting is what's adding "
                          "error on digital-native PDFs, vs. genuine content loss.")
    args = ap.parse_args()
 
    pipeline_name = "docling" if args.mode == "full" else "docling_simple"
    run_id = get_run_id()
    out_root = BASE / "results" / "runs" / run_id / pipeline_name
 
    print(f"Loading Docling converter (mode={args.mode}; downloads its models on first run if mode=full) ...")
    converter = build_converter(args.mode)
 
    dataset_count = 0
    for dataset_name, _, docs in iter_dataset_samples(SAMPLE_ROOT):
        if args.dataset and dataset_name != args.dataset:
            continue
        # Docling here is the PDF text-layer path specifically -- skip
        # anything that isn't a PDF rather than error on it.
        docs = [d for d in docs if d.suffix.lower() == ".pdf"]
        if args.limit:
            docs = docs[: args.limit]
        if not docs:
            continue
        dataset_count += 1
 
        out_dir = out_root / dataset_name
        out_dir.mkdir(parents=True, exist_ok=True)
        timings = []
 
        for doc_path in tqdm(docs, desc=f"Docling[{args.mode}] [{dataset_name}]"):
            doc_id = doc_path.stem
            if (out_dir / f"{doc_id}.md").exists():
                continue  # resumable -- skip already-processed docs on rerun
            start = time.perf_counter()
            try:
                result = converter.convert(str(doc_path))
                text = result.document.export_to_markdown()
                status = "ok"
            except Exception as e:
                text, status = "", f"error: {e}"
            elapsed = time.perf_counter() - start
 
            (out_dir / f"{doc_id}.md").write_text(text, encoding="utf-8")
            timings.append({"doc_id": doc_id, "seconds": elapsed, "status": status})
 
        (out_dir / "_timings.json").write_text(json.dumps(timings, indent=2))
        write_run_manifest(
            out_dir, pipeline=pipeline_name, model_repo=f"docling ({args.mode} mode, local text/layout parser, no HF model id)",
            model_revision="n/a", prompt_variant="n/a", prompt_text="n/a — deterministic parsing, no prompt",
            decoding_params={}, dataset_name=dataset_name, n_docs=len(docs),
        )
        n_errors = sum(1 for t in timings if t["status"] != "ok")
        print(f"[{dataset_name}] done. {len(timings)} docs, {n_errors} errors -> {out_dir}")
 
    if dataset_count == 0:
        print(f"WARNING: no matching PDF dataset(s) under {SAMPLE_ROOT}. Run build_sample.py first.")
 
 
if __name__ == "__main__":
    main()