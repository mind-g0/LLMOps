import json
import os
from datetime import datetime
from pathlib import Path

from PIL import Image

# Shared across every run_*.py script on purpose: if each pipeline rendered
# PDFs at a different DPI, any accuracy difference between models would be
# partly a preprocessing artifact, not a model difference. One constant,
# used everywhere, keeps the comparison fair.
PDF_RENDER_DPI = 200

# NOT applied by default anymore. Start every pilot with a model's own raw
# defaults (do_sample=False only, for reproducibility) -- forcing the same
# repetition_penalty/no_repeat_ngram_size on every model regardless of
# whether it actually loops is just as risky as feeding every model the
# same prompt: a model tuned by its authors for plain greedy decoding can
# get WORSE, not better, from an externally-bolted-on repetition penalty.
#
# Workflow: run the pilot with RAW_DECODING for all 4 models. Only for a
# model whose pilot output actually shows repetition/looping (compute_
# metrics.py's diagnose() calls this out as "ADDING TEXT") do you add an
# override -- put it in PER_MODEL_DECODING_OVERRIDES below, with a comment
# saying which pilot symptom justified it. Don't add overrides pre-emptively.
RAW_DECODING = dict(do_sample=False)

# Keys can be a plain pipeline name (applies to all its datasets) OR a
# (pipeline, dataset) tuple (applies only there) -- added because evidence
# can be dataset-specific: e.g. Qianfan showed insertion-rate as the single
# largest error component on its Arabic documents (repetition tendency
# specifically there), while its resume_dataset_hf run was already clean
# ("usable" diagnosis, no repetition issue). A pipeline-wide override would
# risk fixing one dataset by breaking the other.
PER_MODEL_DECODING_OVERRIDES: dict = {
    # ("qianfan_ocr", "synthetic_cv"): dict(repetition_penalty=1.15, no_repeat_ngram_size=4),
    #   -- candidate fix based on real N=200 evidence: ins_rate exceeded
    #   sub_rate+del_rate combined on this pipeline's Arabic-heavy runs.
    #   Uncomment, re-run ONLY this pipeline/dataset, and compare the new
    #   diagnosis (and the per-language [ar] breakdown) before deciding to
    #   keep it -- don't assume it helps, and check it doesn't hurt English.
}

MAX_NEW_TOKENS_DEFAULT = 4096  # was cut to 2048 for speed in earlier drafts -- don't; that's what causes truncated fields


def get_decoding(pipeline_name: str, dataset_name: str | None = None) -> dict:
    """Raw defaults for everyone, plus whatever override real evidence
    justified -- checked most-specific first: (pipeline, dataset), then
    pipeline alone, else plain raw. Never a blanket guess."""
    if dataset_name and (pipeline_name, dataset_name) in PER_MODEL_DECODING_OVERRIDES:
        return {**RAW_DECODING, **PER_MODEL_DECODING_OVERRIDES[(pipeline_name, dataset_name)]}
    return {**RAW_DECODING, **PER_MODEL_DECODING_OVERRIDES.get(pipeline_name, {})}
 
 
def build_pipeline(model_id: str, revision: str = "main", trust_remote_code: bool = False,
                    min_pixels: int | None = None, max_pixels: int | None = None,
                    device: int | None = None, quantize: str | None = None):
    """Shared loader for the pipeline() wrapper.
 
    device: GPU index to load onto. Defaults to the CUDA_DEVICE env var if
    set, else 0. Lets you point a run at an idle GPU on a shared box
    without killing anyone else's job on GPU 0.
 
    quantize: None (bf16, full footprint) | "8bit" | "4bit" -- via
    bitsandbytes, for fitting a model into limited free VRAM on a shared
    GPU instead of waiting or reducing someone else's job. 8bit roughly
    halves weight memory; 4bit roughly quarters it, at some quality cost --
    treat 4bit as a "make it fit today" option, not a benchmark-standard
    setting, and say so explicitly if you use it for the real 200-sample run.
 
    1-3 above, plus the two below, are the real fixes over a bare
    `pipeline("image-text-to-text", model=model_id)` call:
 
    1. min_pixels/max_pixels -- for Qwen-VL-family models (Qari, Qwen3-VL;
       verify before relying on it for any other architecture, since this
       is that family's own processor kwarg, not a universal one), this is
       the single biggest lever on OCR ACCURACY, not just speed: it sets
       how many visual tokens the image is broken into. The model's own
       default range is huge (4-16384 tokens/image per Qwen's own docs) --
       too low and small print/diacritics genuinely become illegible to
       the model (a real accuracy loss, not a benchmark artifact); too
       high wastes compute for no quality gain past the point where the
       image is already legible. Confirmed via Qwen's own model cards:
       min_pixels/max_pixels are set on the PROCESSOR, not the top-level
       pipeline() call -- pipeline() does accept a pre-built `processor`
       object, which is what makes this configurable without patching
       library internals. A resume scanned at typical DPI needs more
       visual tokens than a product photo; don't leave this at the
       library's generic default without checking it against a few actual
       samples first.
    2. low_cpu_mem_usage=True -- faster, lighter-footprint loading, no
       downside, just previously omitted.
 
    Also prints the model's own generation_config after loading -- this is
    what "raw defaults" in RAW_DECODING actually resolves to for THIS
    model, so it's visible rather than assumed.
    """
    import torch
    from transformers import pipeline as hf_pipeline
 
    device = device if device is not None else int(os.environ.get("CUDA_DEVICE", 0))
 
    kwargs = dict(model=model_id, revision=revision, trust_remote_code=trust_remote_code,
                  dtype=torch.bfloat16, device=device,
                  model_kwargs={"attn_implementation": "sdpa", "low_cpu_mem_usage": True})
 
    if quantize in ("8bit", "4bit"):
        from transformers import BitsAndBytesConfig
        bnb_kwargs = ({"load_in_8bit": True} if quantize == "8bit"
                      else {"load_in_4bit": True, "bnb_4bit_compute_dtype": torch.bfloat16})
        kwargs["model_kwargs"]["quantization_config"] = BitsAndBytesConfig(**bnb_kwargs)
        kwargs["model_kwargs"].pop("low_cpu_mem_usage", None)  # implied by quantized loading, avoid clashing
        kwargs.pop("device", None)  # quantized models place themselves via device_map, not a plain device=
        kwargs["model_kwargs"]["device_map"] = {"": device}
        print(f"[{model_id}] loading with {quantize} quantization (bitsandbytes) on GPU {device} "
              f"-- fits in less VRAM at some quality cost; note this in the report if used for real results.")
    elif quantize is not None:
        raise ValueError(f"quantize must be None, '8bit' or '4bit', got {quantize!r}")
 
    if min_pixels is not None or max_pixels is not None:
        try:
            from transformers import AutoProcessor
            processor = AutoProcessor.from_pretrained(
                model_id, revision=revision, trust_remote_code=trust_remote_code,
                min_pixels=min_pixels, max_pixels=max_pixels,
            )
            kwargs["processor"] = processor
        except TypeError:
            print(f"WARNING: {model_id}'s processor doesn't accept min_pixels/max_pixels "
                  f"(architecture-specific, not universal) — loading with its own defaults instead.")
 
    pipe = hf_pipeline("image-text-to-text", **kwargs)
    try:
        print(f"[{model_id}] model's own generation_config (this is what 'raw' decoding "
              f"actually means for this model): {pipe.model.generation_config}")
    except Exception:
        pass
    return pipe
 
 
def build_processor_and_model(model_id: str, revision: str = "main", trust_remote_code: bool = False,
                               min_pixels: int | None = None, max_pixels: int | None = None,
                               device: int | None = None, quantize: str | None = None):
    """Same loading logic as build_pipeline(), but returns (processor, model)
    directly instead of a pipeline() wrapper. Needed whenever a call needs
    to control something the high-level pipeline() doesn't reliably forward
    -- e.g. enable_thinking=False for Qwen3-series models, which default to
    generating a whole <think>...</think> reasoning block before the actual
    answer (real latency cost, and not needed for a transcription task)."""
    import torch
    from transformers import AutoProcessor, AutoModelForImageTextToText
 
    device = device if device is not None else int(os.environ.get("CUDA_DEVICE", 0))
    model_kwargs = dict(revision=revision, trust_remote_code=trust_remote_code,
                         dtype=torch.bfloat16, attn_implementation="sdpa")
 
    if quantize in ("8bit", "4bit"):
        from transformers import BitsAndBytesConfig
        bnb_kwargs = ({"load_in_8bit": True} if quantize == "8bit"
                      else {"load_in_4bit": True, "bnb_4bit_compute_dtype": torch.bfloat16})
        model_kwargs["quantization_config"] = BitsAndBytesConfig(**bnb_kwargs)
        model_kwargs["device_map"] = {"": device}
        print(f"[{model_id}] loading with {quantize} quantization on GPU {device} -- "
              f"note this in your report if used for the real 200-sample run.")
    elif quantize is not None:
        raise ValueError(f"quantize must be None, '8bit' or '4bit', got {quantize!r}")
    else:
        model_kwargs["device_map"] = {"": device}
        model_kwargs["low_cpu_mem_usage"] = True
 
    processor_kwargs = dict(revision=revision, trust_remote_code=trust_remote_code)
    if min_pixels is not None or max_pixels is not None:
        try:
            processor = AutoProcessor.from_pretrained(
                model_id, min_pixels=min_pixels, max_pixels=max_pixels, **processor_kwargs)
        except TypeError:
            print(f"WARNING: {model_id}'s processor doesn't accept min_pixels/max_pixels "
                  f"(architecture-specific, not universal) — loading with its own defaults instead.")
            processor = AutoProcessor.from_pretrained(model_id, **processor_kwargs)
    else:
        processor = AutoProcessor.from_pretrained(model_id, **processor_kwargs)
 
    model = AutoModelForImageTextToText.from_pretrained(model_id, **model_kwargs)
    try:
        print(f"[{model_id}] model's own generation_config (this is what 'raw' decoding "
              f"actually means for this model): {model.generation_config}")
    except Exception:
        pass
    return processor, model
 
 
def load_image_pages(path: Path, dpi: int = PDF_RENDER_DPI) -> list[Image.Image]:
    """Every page of a PDF, not just the first -- taking page 1 only is
    what silently produced blank Education/Experience fields on multi-page
    resumes before. Returns a list even for single images/pages."""
    if path.suffix.lower() == ".pdf":
        from pdf2image import convert_from_path
        return convert_from_path(str(path), dpi=dpi)
    return [Image.open(path).convert("RGB")]
 
 
def load_env_file(*paths: Path) -> None:
    """Minimal .env loader using only stdlib -- no python-dotenv dependency.
    Checks each given path in order (first match wins), plus an ENV_FILE
    environment variable override if set, so a project layout with .env
    outside the repo root doesn't require guessing again. Parses KEY=VALUE
    lines, skips blanks and '#' comments, strips surrounding quotes, and
    never overwrites a variable already set in the real shell environment
    (same precedence python-dotenv uses)."""
    candidates = []
    if os.environ.get("ENV_FILE"):
        candidates.append(Path(os.environ["ENV_FILE"]))
    candidates.extend(paths)
 
    found = next((p for p in candidates if p.exists()), None)
    if found is None:
        checked = ", ".join(str(p) for p in candidates)
        print(f"NOTE: no .env file found. Checked: {checked}. "
              f"Set ENV_FILE=/path/to/.env to point at a different location, "
              f"or relying on already-exported environment variables instead.")
        return
 
    n_set = 0
    for line in found.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value
            n_set += 1
    print(f"Loaded {n_set} variable(s) from {found}")
 
 
def iter_dataset_samples(sample_root: Path):
    """Yield (dataset_name, dataset_sample_dir, [doc_paths]) for each
    per-dataset subfolder under data/samples/. Skips empty/missing ones."""
    if not sample_root.exists():
        return
    for dataset_dir in sorted(p for p in sample_root.iterdir() if p.is_dir()):
        docs = sorted(p for p in dataset_dir.glob("doc_*.*"))
        if docs:
            yield dataset_dir.name, dataset_dir, docs
 
 
def get_run_id() -> str:
    """Every script in one terminal session should write into the same
    results/runs/<RUN_ID>/ folder. Set once per session with
    `source start_new_run.sh`. Falls back to a fresh timestamp otherwise."""
    run_id = os.environ.get("BENCHMARK_RUN_ID")
    if not run_id:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        print(f"NOTE: BENCHMARK_RUN_ID not set — using '{run_id}' for this script only.")
        print(f"      To group a full pass into one run folder: source start_new_run.sh")
    return run_id
 
 
def write_run_manifest(out_dir: Path, *, pipeline: str, model_repo: str,
                        model_revision: str, prompt_variant: str, prompt_text: str,
                        decoding_params: dict, dataset_name: str, n_docs: int,
                        quantize: str | None = None):
    """A benchmark result without this is not reproducible — write it next
    to every results/<pipeline>/<dataset>/ output directory, every run.
    quantize is recorded explicitly: a resumable run mixing a quantized
    pilot's leftover docs with a later full-precision pass would otherwise
    have no visible marker of which docs came from which condition."""
    try:
        import torch
        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
        torch_version = torch.__version__
    except ImportError:
        gpu, torch_version = "unknown", "unknown"
    try:
        import transformers
        transformers_version = transformers.__version__
    except ImportError:
        transformers_version = "unknown"
 
    manifest = {
        "pipeline": pipeline, "model_repo": model_repo, "model_revision": model_revision,
        "prompt_variant": prompt_variant, "prompt_text": prompt_text,
        "decoding_params": decoding_params, "dataset_name": dataset_name, "n_docs": n_docs,
        "quantize": quantize or "none (full precision)",
        "gpu": gpu, "torch_version": torch_version, "transformers_version": transformers_version,
        "timestamp": datetime.now().isoformat(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")