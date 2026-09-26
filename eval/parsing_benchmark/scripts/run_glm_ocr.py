import argparse
import json
import os
import time
from pathlib import Path
 
import torch
from tqdm import tqdm
from transformers import AutoProcessor, AutoModelForImageTextToText
 
from dataset_utils import (iter_dataset_samples, get_run_id, write_run_manifest,
                            load_image_pages, get_decoding, MAX_NEW_TOKENS_DEFAULT)
from prompts import get_prompt
 
BASE = Path(__file__).parent.parent
SAMPLE_ROOT = BASE / "data" / "samples"
PIPELINE_NAME = "glm_ocr"
MODEL_ID = "zai-org/GLM-OCR"
MODEL_REVISION = "main"
 
 
def run_one_doc(processor, model, prompt: str, doc_path: Path, decoding: dict) -> tuple[str, int]:
    pages = load_image_pages(doc_path)
    texts = []
    for page_img in pages:
        messages = [{"role": "user", "content": [
            {"type": "image", "image": page_img}, {"type": "text", "text": prompt},
        ]}]
        inputs = processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt",
        ).to(model.device)
        output_ids = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS_DEFAULT, **decoding)
        new_tokens = output_ids[0][inputs["input_ids"].shape[-1]:]
        texts.append(processor.decode(new_tokens, skip_special_tokens=True))
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
 
    print(f"Loading {MODEL_ID} (revision={MODEL_REVISION}) ...")
    device = args.device if args.device is not None else int(os.environ.get("CUDA_DEVICE", 0))
    model_kwargs = dict(revision=MODEL_REVISION, trust_remote_code=True,
                         dtype=torch.bfloat16, attn_implementation="sdpa")
    if args.quantize in ("8bit", "4bit"):
        from transformers import BitsAndBytesConfig
        bnb_kwargs = ({"load_in_8bit": True} if args.quantize == "8bit"
                      else {"load_in_4bit": True, "bnb_4bit_compute_dtype": torch.bfloat16})
        model_kwargs["quantization_config"] = BitsAndBytesConfig(**bnb_kwargs)
        model_kwargs["device_map"] = {"": device}
        print(f"[{MODEL_ID}] loading with {args.quantize} quantization on GPU {device} -- "
              f"note this in your report if used for the real 200-sample run.")
    else:
        model_kwargs["device_map"] = {"": device}
        model_kwargs["low_cpu_mem_usage"] = True
    processor = AutoProcessor.from_pretrained(MODEL_ID, revision=MODEL_REVISION, trust_remote_code=True)
    model = AutoModelForImageTextToText.from_pretrained(MODEL_ID, **model_kwargs)
    print(f"[{MODEL_ID}] model's own generation_config (this is what 'raw' decoding "
          f"actually means for this model): {model.generation_config}")
 
    dataset_count = 0
    for dataset_name, _, docs in iter_dataset_samples(SAMPLE_ROOT):
        if args.dataset and dataset_name != args.dataset:
            continue
        if args.limit:
            docs = docs[: args.limit]
        dataset_count += 1
 
        prompt = get_prompt(PIPELINE_NAME, args.variant, dataset_name)
        decoding = get_decoding(PIPELINE_NAME, dataset_name)
        out_dir = out_root / dataset_name
        out_dir.mkdir(parents=True, exist_ok=True)
        timings = []
 
        for doc_path in tqdm(docs, desc=f"GLM-OCR [{dataset_name}]"):
            doc_id = doc_path.stem
            if (out_dir / f"{doc_id}.md").exists():
                continue
            start = time.perf_counter()
            try:
                text, n_pages = run_one_doc(processor, model, prompt, doc_path, decoding)
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
            dataset_name=dataset_name, n_docs=len(docs), quantize=args.quantize,
        )
        n_errors = sum(1 for t in timings if t["status"] != "ok")
        print(f"[{dataset_name}] done. {len(timings)} docs, {n_errors} errors -> {out_dir}")
        if dataset_name == "synthetic_cv":
            print(f"[{dataset_name}] reminder: GLM-OCR does not document Arabic support — "
                  f"treat weak numbers on this dataset's Arabic half as a capability finding, "
                  f"not a bug to chase (check the per-language [ar]/[en] split in compute_metrics.py).")
 
    if dataset_count == 0:
        print(f"WARNING: no matching dataset(s) under {SAMPLE_ROOT}. Run build_sample.py first.")
 
 
if __name__ == "__main__":
    main()