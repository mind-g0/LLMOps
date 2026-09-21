import argparse
import json
import time
from pathlib import Path
 
from tqdm import tqdm
 
from dataset_utils import (iter_dataset_samples, get_run_id, write_run_manifest, build_pipeline,
                            load_image_pages, get_decoding, MAX_NEW_TOKENS_DEFAULT)
from prompts import get_prompt
 
BASE = Path(__file__).parent.parent
SAMPLE_ROOT = BASE / "data" / "samples"
PIPELINE_NAME = "qianfan_ocr"
MODEL_ID = "baidu/Qianfan-OCR"
MODEL_REVISION = "main"
# Qianfan-OCR uses a custom Qianfan-ViT encoder, NOT the standard Qwen-VL
# vision tower -- min_pixels/max_pixels is a Qwen-VL processor convention
# and is NOT confirmed to apply here. build_pipeline() tries it and falls
# back to the model's own default resolution handling with a warning if
# the processor rejects the kwarg -- check that warning doesn't fire
# before assuming this is doing anything for this specific model.
MIN_PIXELS, MAX_PIXELS = 256 * 28 * 28, 1280 * 28 * 28
 
 
def run_one_doc(pipe, prompt: str, doc_path: Path, decoding: dict) -> tuple[str, int]:
    pages = load_image_pages(doc_path)
    texts = []
    for page_img in pages:
        messages = [{"role": "user", "content": [
            {"type": "image", "image": page_img}, {"type": "text", "text": prompt},
        ]}]
        output = pipe(text=messages, max_new_tokens=MAX_NEW_TOKENS_DEFAULT, **decoding)
        texts.append(output[0]["generated_text"][-1]["content"])
    return "\n\n".join(texts), len(pages)
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="native", choices=["native", "control", "task"])
    ap.add_argument("--dataset", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--device", type=int, default=None,
                     help="GPU index (default: CUDA_DEVICE env var, else 0) -- "
                          "use this to run on an idle GPU on a shared box without touching anyone else's job")
    ap.add_argument("--quantize", choices=["8bit", "4bit"], default=None,
                     help="bitsandbytes quantization if VRAM is tight; note in your report if used")
    args = ap.parse_args()
 
    run_id = get_run_id()
    variant_suffix = "" if args.variant == "native" else f"__{args.variant}"
    out_root = BASE / "results" / "runs" / run_id / f"{PIPELINE_NAME}{variant_suffix}"
 
    decoding = get_decoding(PIPELINE_NAME)
    print(f"Loading {MODEL_ID} (revision={MODEL_REVISION}) ...")
    pipe = build_pipeline(MODEL_ID, MODEL_REVISION, trust_remote_code=True,
                           min_pixels=MIN_PIXELS, max_pixels=MAX_PIXELS,
                           device=args.device, quantize=args.quantize)
 
    dataset_count = 0
    for dataset_name, _, docs in iter_dataset_samples(SAMPLE_ROOT):
        if args.dataset and dataset_name != args.dataset:
            continue
        if args.limit:
            docs = docs[: args.limit]
        dataset_count += 1
 
        prompt = get_prompt(PIPELINE_NAME, args.variant, dataset_name)
        out_dir = out_root / dataset_name
        out_dir.mkdir(parents=True, exist_ok=True)
        timings = []
 
        for doc_path in tqdm(docs, desc=f"Qianfan-OCR [{dataset_name}]"):
            doc_id = doc_path.stem
            if (out_dir / f"{doc_id}.md").exists():
                continue
            start = time.perf_counter()
            try:
                text, n_pages = run_one_doc(pipe, prompt, doc_path, decoding)
                status = "ok"
            except Exception as e:
                text, n_pages, status = "", None, f"error: {e}"
            elapsed = time.perf_counter() - start
 
            (out_dir / f"{doc_id}.md").write_text(text, encoding="utf-8")
            timings.append({"doc_id": doc_id, "seconds": elapsed, "n_pages": n_pages, "status": status})
 
        (out_dir / "_timings.json").write_text(json.dumps(timings, indent=2))
        write_run_manifest(
            out_dir, pipeline=PIPELINE_NAME, model_repo=MODEL_ID, model_revision=MODEL_REVISION,
            prompt_variant=args.variant, prompt_text=prompt,
            decoding_params={**decoding, "max_new_tokens": MAX_NEW_TOKENS_DEFAULT},
            dataset_name=dataset_name, n_docs=len(docs),
        )
        n_errors = sum(1 for t in timings if t["status"] != "ok")
        print(f"[{dataset_name}] done. {len(timings)} docs, {n_errors} errors -> {out_dir}")
 
    if dataset_count == 0:
        print(f"WARNING: no matching dataset(s) under {SAMPLE_ROOT}. Run build_sample.py first.")
 
 
if __name__ == "__main__":
    main()
 