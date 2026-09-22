"""
Pipeline — Claude Haiku (Anthropic), via OpenRouter API.

Different shape from the other 5 pipelines: this is an API call, not a
local GPU model. No build_pipeline()/build_processor_and_model(), no
trust_remote_code, no quantization. Cost is real money per call, so this
script logs ACTUAL token usage from every response into _timings.json --
after a pilot run, read that back to get a real cost figure instead of
trusting an estimate. Rough ballpark before running: ~$2 for a full
400-document pass (200 x 2 datasets), based on Claude Haiku 4.5 pricing
($1/M input, $5/M output) and Anthropic's image-tokenization formula
(tokens ~ width*height/750, capped after auto-resize) -- confirm this
against the real numbers in _timings.json rather than trusting it.

Prompt: same task-shaped prompts.py registry as the other general models
(no fixed "native" instruction -- Claude is a general instruct model, not
an OCR fine-tune).

Multi-page PDFs: reuses load_image_pages() like the local pipelines, one
image per page, concatenated -- same page-completeness fix as everywhere
else in this benchmark.

Deps (uv pip):
    uv pip install openrouter tqdm pillow

Run:
    export OPENROUTER_API_KEY=sk-or-...   # or put it in .env, same as OPENAI_API_KEY
    python run_claude_haiku.py --variant native --limit 20   # pilot -- check real cost here first
"""

import argparse
import base64
import io
import json
import os
import time
from pathlib import Path

from tqdm import tqdm
from openrouter import OpenRouter

from dataset_utils import iter_dataset_samples, get_run_id, write_run_manifest, load_image_pages, load_env_file
from prompts import get_prompt

BASE = Path(__file__).parent.parent
SAMPLE_ROOT = BASE / "data" / "samples"
PIPELINE_NAME = "claude_haiku"
MODEL_ID = "~anthropic/claude-haiku-latest"  # OpenRouter model string, as given
MAX_TOKENS = 4096

load_env_file(BASE / ".env", BASE.parent / ".env")


def image_to_data_url(img) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def run_one_doc(client, prompt: str, doc_path: Path) -> tuple[str, int, int, int]:
    """Returns (text, n_pages, input_tokens, output_tokens) -- token counts
    are the REAL numbers read back from the API response, not estimates."""
    pages = load_image_pages(doc_path)
    texts = []
    total_in = total_out = 0
    for page_img in pages:
        response = client.chat.send(
            model=MODEL_ID,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_to_data_url(page_img)}},
                ],
            }],
            max_tokens=MAX_TOKENS,
        )
        texts.append(response.choices[0].message.content)
        usage = getattr(response, "usage", None)
        if usage:
            total_in += getattr(usage, "prompt_tokens", 0) or 0
            total_out += getattr(usage, "completion_tokens", 0) or 0
    return "\n\n".join(texts), len(pages), total_in, total_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="native", choices=["native", "control"])
    ap.add_argument("--dataset", default=None)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit(
            f"OPENROUTER_API_KEY not found. Checked {BASE / '.env'} and {BASE.parent / '.env'} "
            f"(plus ENV_FILE if set), plus already-exported environment variables."
        )

    run_id = get_run_id()
    variant_suffix = "" if args.variant == "native" else f"__{args.variant}"
    out_root = BASE / "results" / "runs" / run_id / f"{PIPELINE_NAME}{variant_suffix}"

    dataset_count = 0
    grand_total_in = grand_total_out = 0

    with OpenRouter(api_key=os.environ["OPENROUTER_API_KEY"]) as client:
        for dataset_name, _, docs in iter_dataset_samples(SAMPLE_ROOT):
            if args.dataset and dataset_name != args.dataset:
                continue
            docs = [d for d in docs if d.suffix.lower() in (".pdf", ".png", ".jpg", ".jpeg")]
            if args.limit:
                docs = docs[: args.limit]
            if not docs:
                continue
            dataset_count += 1

            prompt = get_prompt(PIPELINE_NAME, args.variant, dataset_name)

            out_dir = out_root / dataset_name
            out_dir.mkdir(parents=True, exist_ok=True)
            timings = []
            dataset_total_in = dataset_total_out = 0

            for doc_path in tqdm(docs, desc=f"Claude Haiku [{dataset_name}]"):
                doc_id = doc_path.stem
                if (out_dir / f"{doc_id}.md").exists():
                    continue  # resumable
                start = time.perf_counter()
                try:
                    text, n_pages, in_tok, out_tok = run_one_doc(client, prompt, doc_path)
                    status = "ok"
                except Exception as e:
                    text, n_pages, in_tok, out_tok, status = "", None, 0, 0, f"error: {e}"
                elapsed = time.perf_counter() - start

                (out_dir / f"{doc_id}.md").write_text(text, encoding="utf-8")
                timings.append({"doc_id": doc_id, "seconds": elapsed, "n_pages": n_pages,
                                 "input_tokens": in_tok, "output_tokens": out_tok, "status": status})
                dataset_total_in += in_tok
                dataset_total_out += out_tok

            (out_dir / "_timings.json").write_text(json.dumps(timings, indent=2))
            write_run_manifest(
                out_dir, pipeline=PIPELINE_NAME, model_repo=MODEL_ID, model_revision="n/a (API, versionless)",
                prompt_variant=args.variant, prompt_text=prompt,
                decoding_params={"max_tokens": MAX_TOKENS},
                dataset_name=dataset_name, n_docs=len(docs),
            )
            n_errors = sum(1 for t in timings if t["status"] != "ok")
            est_cost = dataset_total_in / 1_000_000 * 1.00 + dataset_total_out / 1_000_000 * 5.00
            print(f"[{dataset_name}] done. {len(timings)} docs, {n_errors} errors -> {out_dir}")
            print(f"[{dataset_name}] REAL token usage this run: {dataset_total_in} in / "
                  f"{dataset_total_out} out -- approx ${est_cost:.4f} at $1/$5 per M "
                  f"(verify against your actual OpenRouter billing, this is Haiku 4.5's list price, "
                  f"OpenRouter may differ slightly)")
            grand_total_in += dataset_total_in
            grand_total_out += dataset_total_out

    if dataset_count == 0:
        print(f"WARNING: no matching dataset(s) under {SAMPLE_ROOT}. Run build_sample.py first.")
    else:
        est_cost = grand_total_in / 1_000_000 * 1.00 + grand_total_out / 1_000_000 * 5.00
        print(f"\nTOTAL this run: {grand_total_in} input tokens, {grand_total_out} output tokens "
              f"-- approx ${est_cost:.4f}")


if __name__ == "__main__":
    main()