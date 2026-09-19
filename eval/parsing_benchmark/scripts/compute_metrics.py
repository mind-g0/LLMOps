import argparse
import json
import re
import unicodedata
from pathlib import Path
 
import numpy as np
import pandas as pd
from jiwer import process_characters, process_words
from rapidfuzz import fuzz
 
from arabic_normalize import normalize_arabic  # your existing module -- restored, was dropped by mistake
 
BASE = Path(__file__).parent.parent
GT_ROOT = BASE / "data" / "ground_truth"
METRICS_DIR = BASE / "reports" / "metrics"
 
RESUME_DATASETS = {"resume_dataset_hf", "synthetic_cv"}
N_BOOTSTRAP = 1000
RNG_SEED = 42
DIACRITIC_PRESENCE_FLOOR = 0.03  # below this, treat GT as effectively undiacritized
 
 
# ---------------------------------------------------------------------------
# Text cleaning / CER-WER (unchanged logic from the earlier version, kept
# because it was already correct -- just re-pointed at the new run layout)
# ---------------------------------------------------------------------------
 
def strip_markdown(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"^\s*(```|~~~).*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>\n]{1,200}>", " ", text)
    lines = []
    for line in text.split("\n"):
        if re.fullmatch(r"\s*\|?[\s:|\-]+\|[\s:|\-]*", line) and "-" in line:
            continue
        if re.fullmatch(r"\s*([-*_])\1{2,}\s*", line):
            continue
        line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
        line = re.sub(r"^\s*>+\s*", "", line)
        line = re.sub(r"^\s*[-*+]\s+", "", line)
        lines.append(line)
    text = "\n".join(lines)
    text = text.replace("|", " ").replace("`", "").replace("*", "")
    return re.sub(r"\s+", " ", text.strip().lower())
 
 
def normalize(text: str) -> str:
    return strip_markdown(unicodedata.normalize("NFKC", text or ""))
 
 
def score_text(pred: str, gt: str, is_arabic: bool = False) -> dict:
    """Arabic gets its own normalization path via your arabic_normalize
    module -- diacritics matter for Arabic CER and a plain lowercase/NFKC
    pass silently discards that signal. Non-Arabic text is unaffected."""
    if is_arabic:
        pred_std = normalize_arabic(strip_markdown(pred), strip_diacritics=True)
        gt_std = normalize_arabic(strip_markdown(gt), strip_diacritics=True)
        pred_diac = normalize_arabic(strip_markdown(pred), strip_diacritics=False)
        gt_diac = normalize_arabic(strip_markdown(gt), strip_diacritics=False)
    else:
        pred_std, gt_std = normalize(pred), normalize(gt)
        pred_diac = gt_diac = None
 
    if not gt_std:
        return None
 
    c, w = process_characters(gt_std, pred_std), process_words(gt_std, pred_std)
    ref_chars, ref_words = max(len(gt_std), 1), max(len(gt_std.split()), 1)
    out = {
        "cer": (c.substitutions + c.deletions + c.insertions) / ref_chars,
        "wer": (w.substitutions + w.deletions + w.insertions) / ref_words,
        "word_subs": w.substitutions, "word_dels": w.deletions, "word_ins": w.insertions,
        "ref_words": ref_words,
        "char_subs": c.substitutions, "char_dels": c.deletions, "char_ins": c.insertions,
        "ref_chars": ref_chars,
        "len_ratio": len(pred_std) / len(gt_std) if gt_std else None,
        "is_empty_pred": not pred_std.strip(),
    }
 
    if is_arabic and gt_diac:
        dc = process_characters(gt_diac, pred_diac)
        out["cer_with_diacritics"] = (dc.substitutions + dc.deletions + dc.insertions) / max(len(gt_diac), 1)
        n_diac_chars = sum(1 for ch in gt_diac if unicodedata.combining(ch))
        out["gt_diacritic_frac"] = n_diac_chars / max(len(gt_diac), 1)
    return out
 
 
# ---------------------------------------------------------------------------
# Field-level scoring -- FUNSD/CORD/SROIE-style exact-match F1, with grouped
# record matching for education[]/experience[] (CORD/KIEval convention).
# ---------------------------------------------------------------------------
 
FUZZY_MATCH_THRESHOLD = 90
 
 
def _norm(s) -> str:
    return normalize(str(s)) if s is not None else ""
 
 
def score_atomic_fields(pred: dict, gt: dict, fields=("name", "email", "phone")) -> dict:
    out = {}
    for f in fields:
        gt_val, pred_val = gt.get(f), pred.get(f)
        if not gt_val:
            continue  # field absent from ground truth -- not scoreable, not a miss
        out[f] = int(fuzz.ratio(_norm(pred_val), _norm(gt_val)) >= FUZZY_MATCH_THRESHOLD)
    return out
 
 
def score_skills(pred_skills: list, gt_skills: list, threshold: int = FUZZY_MATCH_THRESHOLD) -> dict | None:
    """Fuzzy-matched, NOT exact-set intersection. Skill names legitimately
    vary in phrasing between a human-labeled ground truth and a model's own
    extraction ("AWS" vs "Amazon Web Services", "ML" vs "Machine Learning",
    or just different capitalization/punctuation) -- exact string matching
    scores a genuinely correct extraction as a miss whenever the wording
    differs at all. Greedy best-match bipartite pairing instead, same
    approach as match_records() below for grouped fields.
 
    Caveat, worth stating explicitly wherever this number is reported: this
    still only catches near-identical phrasing (typos, case, minor wording)
    -- it will NOT match true synonym pairs with low string similarity like
    "ML" vs "Machine Learning". Closing that gap needs a canonical skill
    taxonomy (exactly what your own capstone's Phase 4 Skill Normalization
    step is for), not string-distance matching. Don't read a residual score
    below 1.0 here as pure extraction error without checking whether
    unmatched pairs are actually synonyms first.
    """
    if not gt_skills:
        return None
    gt_list = [_norm(s) for s in gt_skills]
    pred_list = [_norm(s) for s in (pred_skills or [])]
    if not pred_list:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
 
    scores = [[fuzz.ratio(p, g) for g in gt_list] for p in pred_list]
    flat = sorted(
        ((scores[i][j], i, j) for i in range(len(pred_list)) for j in range(len(gt_list))),
        reverse=True,
    )
    pairs, used_p, used_g = [], set(), set()
    for score, i, j in flat:
        if i in used_p or j in used_g or score < threshold:
            break  # flat is sorted descending -- everything after this is also below threshold
        pairs.append((i, j)); used_p.add(i); used_g.add(j)
 
    tp = len(pairs)
    p = tp / len(pred_list)
    r = tp / len(gt_list)
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return {"precision": p, "recall": r, "f1": f1}
 
 
def match_records(pred_records: list, gt_records: list, key_fields: list) -> list:
    """Greedy best-match pairing by average field similarity across
    key_fields (CORD/KIEval-style grouped-entity matching). Returns list of
    (pred_idx_or_None, gt_idx_or_None) -- unmatched entries on either side
    are precision/recall misses, not silently dropped."""
    if not gt_records:
        return [(i, None) for i in range(len(pred_records or []))]
    if not pred_records:
        return [(None, j) for j in range(len(gt_records))]
 
    scores = np.zeros((len(pred_records), len(gt_records)))
    for i, p in enumerate(pred_records):
        for j, g in enumerate(gt_records):
            sims = [fuzz.ratio(_norm(p.get(f)), _norm(g.get(f))) for f in key_fields if g.get(f)]
            scores[i, j] = sum(sims) / len(sims) if sims else 0.0
 
    pairs, used_p, used_g = [], set(), set()
    flat = sorted(((scores[i, j], i, j) for i in range(len(pred_records)) for j in range(len(gt_records))),
                  reverse=True)
    for score, i, j in flat:
        if i in used_p or j in used_g or score < FUZZY_MATCH_THRESHOLD:
            break
        pairs.append((i, j)); used_p.add(i); used_g.add(j)
    pairs += [(i, None) for i in range(len(pred_records)) if i not in used_p]
    pairs += [(None, j) for j in range(len(gt_records)) if j not in used_g]
    return pairs
 
 
def score_grouped(pred_list: list, gt_list: list, key_fields: list, score_fields: list) -> dict | None:
    if not gt_list:
        return None
    pairs = match_records(pred_list or [], gt_list, key_fields)
    matched = [(i, j) for i, j in pairs if i is not None and j is not None]
    tp_records, fp_records, fn_records = len(matched), sum(1 for i, j in pairs if j is None), \
        sum(1 for i, j in pairs if i is None)
 
    field_hits = field_total = 0
    for i, j in matched:
        for f in score_fields:
            gt_val = gt_list[j].get(f)
            if gt_val in (None, ""):
                continue
            field_total += 1
            field_hits += int(fuzz.ratio(_norm(pred_list[i].get(f)), _norm(gt_val)) >= FUZZY_MATCH_THRESHOLD)
 
    record_p = tp_records / (tp_records + fp_records) if (tp_records + fp_records) else 0.0
    record_r = tp_records / (tp_records + fn_records) if (tp_records + fn_records) else 0.0
    return {
        "record_precision": record_p, "record_recall": record_r,
        "record_f1": 2 * record_p * record_r / (record_p + record_r) if (record_p + record_r) else 0.0,
        "field_accuracy_within_matched": field_hits / field_total if field_total else None,
    }
 
 
def score_fields_for_doc(pred_fields: dict, gt_fields: dict) -> dict:
    return {
        "atomic": score_atomic_fields(pred_fields, gt_fields),
        "skills": score_skills(pred_fields.get("skills"), gt_fields.get("skills")),
        "education": score_grouped(pred_fields.get("education"), gt_fields.get("education"),
                                    key_fields=["degree", "institution"],
                                    score_fields=["degree", "institution", "start_year", "end_year", "gpa"]),
        "experience": score_grouped(pred_fields.get("experience"), gt_fields.get("experience"),
                                     key_fields=["company", "role"],
                                     score_fields=["company", "role", "start_date", "end_date"]),
    }
 
 
# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------
 
def bootstrap_ci(values: list[float], n_boot: int = N_BOOTSTRAP, seed: int = RNG_SEED) -> tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    arr = np.array(values)
    rng = np.random.default_rng(seed)
    means = [rng.choice(arr, size=len(arr), replace=True).mean() for _ in range(n_boot)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
 
 
# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
 
def load_gt(dataset_name: str, split: str | None):
    gt_dir = GT_ROOT / dataset_name
    out = {}
    for gt_path in sorted(gt_dir.glob("doc_*.json")):
        gt = json.loads(gt_path.read_text())
        if gt.get("needs_human_review", False):
            continue
        if split and gt.get("split") != split:
            continue
        out[gt["doc_id"]] = gt
    return out
 
 
def score_pipeline_dataset(run_id: str, pipeline: str, dataset_name: str, split: str | None):
    gt_by_doc = load_gt(dataset_name, split)
    result_dir = BASE / "results" / "runs" / run_id / pipeline / dataset_name
    text_rows, field_rows = [], []
 
    for doc_id, gt in gt_by_doc.items():
        md_path = result_dir / f"{doc_id}.md"
        pred_text = md_path.read_text(encoding="utf-8") if md_path.exists() else None
 
        if gt.get("ground_truth_text") and pred_text is not None:
            s = score_text(pred_text, gt["ground_truth_text"], is_arabic=(gt.get("detected_language") == "ar"))
            if s:
                text_rows.append({"doc_id": doc_id, "language": gt.get("detected_language"), **s})
 
        if dataset_name in RESUME_DATASETS:
            fields_path = result_dir / f"{doc_id}_fields.json"
            if fields_path.exists():
                payload = json.loads(fields_path.read_text())
                if payload.get("extraction_method") == "llm":
                    field_rows.append({"doc_id": doc_id, "language": gt.get("detected_language"),
                                        **score_fields_for_doc(payload["fields"], gt["ground_truth_fields"])})
 
    return text_rows, field_rows, len(gt_by_doc)
 
 
def summarize_text(rows: list[dict], n_docs: int) -> dict:
    if not rows:
        return {"n_scored": 0, "n_docs": n_docs}
    cers = [r["cer"] for r in rows]
    wers = [r["wer"] for r in rows]
    total_edits = sum(r["char_subs"] + r["char_dels"] + r["char_ins"] for r in rows)
    total_chars = sum(r["ref_chars"] for r in rows)
    total_word_edits = sum(r["word_subs"] + r["word_dels"] + r["word_ins"] for r in rows)
    total_words = sum(r["ref_words"] for r in rows)
    lo, hi = bootstrap_ci(cers)
    wer_lo, wer_hi = bootstrap_ci(wers)
    sub_rate = sum(r["char_subs"] for r in rows) / total_chars
    del_rate = sum(r["char_dels"] for r in rows) / total_chars
    ins_rate = sum(r["char_ins"] for r in rows) / total_chars
    out = {
        "n_scored": len(rows), "n_docs": n_docs,
        "micro_cer": total_edits / total_chars,
        "mean_cer": float(np.mean(cers)),      # unweighted (macro) average -- every doc counts equally
        "median_cer": float(np.median(cers)),  # robust to outliers -- see diagnosis/worst-docs for why this matters
        "cer_ci95_lo": round(lo, 4), "cer_ci95_hi": round(hi, 4),
        "micro_wer": total_word_edits / total_words,
        "mean_wer": float(np.mean(wers)),
        "median_wer": float(np.median(wers)),
        "wer_ci95_lo": round(wer_lo, 4), "wer_ci95_hi": round(wer_hi, 4),
        "n_empty": sum(r["is_empty_pred"] for r in rows),
        "sub_rate": round(sub_rate, 4), "del_rate": round(del_rate, 4), "ins_rate": round(ins_rate, 4),
        "diagnosis": diagnose_errors(sub_rate, del_rate, ins_rate),
    }
    diac_rows = [r for r in rows if r.get("cer_with_diacritics") is not None]
    if diac_rows:
        mean_frac = np.mean([r["gt_diacritic_frac"] for r in diac_rows])
        if mean_frac < DIACRITIC_PRESENCE_FLOOR:
            out["diacritics_note"] = (f"GT is only {mean_frac:.2%} diacritics -- "
                                       f"effectively undiacritized, diacritic-CER omitted as noise")
        else:
            out["cer_with_diacritics_mean"] = float(np.mean([r["cer_with_diacritics"] for r in diac_rows]))
    return out
 
 
def diagnose_errors(sub_rate: float, del_rate: float, ins_rate: float) -> str:
    """Names the DOMINANT failure mode from the substitution/deletion/
    insertion split, so a high CER points at a fixable cause instead of
    just a number. Restored from the original CER-only script -- this was
    dropped when field-scoring was added and needs to stay, since it's
    what tells you whether a model needs a decoding override at all."""
    total = sub_rate + del_rate + ins_rate
    if total < 0.10:
        return "usable"
    if del_rate > 2 * (sub_rate + ins_rate):
        return "DROPPING TEXT (layout/truncation/multi-page issue)"
    if ins_rate > 2 * (sub_rate + del_rate):
        return "ADDING TEXT (repetition loop/preamble -- consider a decoding override for this model)"
    if sub_rate >= max(del_rate, ins_rate):
        return "recognition error (genuine model-quality issue)"
    return "mixed"
 
 
def summarize_fields(rows: list[dict], n_docs: int) -> dict:
    if not rows:
        return {"n_scored": 0, "n_docs": n_docs}
    skills_f1 = [r["skills"]["f1"] for r in rows if r["skills"]]
    edu_acc = [r["education"]["field_accuracy_within_matched"] for r in rows
               if r["education"] and r["education"]["field_accuracy_within_matched"] is not None]
    exp_acc = [r["experience"]["field_accuracy_within_matched"] for r in rows
               if r["experience"] and r["experience"]["field_accuracy_within_matched"] is not None]
    out = {"n_scored": len(rows), "n_docs": n_docs}
    if skills_f1:
        lo, hi = bootstrap_ci(skills_f1)
        out["skills_f1_micro"] = float(np.mean(skills_f1))
        out["skills_f1_ci95_lo"] = round(lo, 4)
        out["skills_f1_ci95_hi"] = round(hi, 4)
    if edu_acc:
        out["education_field_accuracy"] = float(np.mean(edu_acc))
    if exp_acc:
        out["experience_field_accuracy"] = float(np.mean(exp_acc))
    return out
 
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--split", choices=["dev", "test"], default=None,
                     help="omit to score everything; use 'test' for the numbers that go in the report")
    args = ap.parse_args()
 
    run_dir = BASE / "results" / "runs" / args.run_id
    if not run_dir.exists():
        print(f"No run at {run_dir}")
        return
 
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = []
 
    for pipeline_dir in sorted(run_dir.iterdir()):
        if not pipeline_dir.is_dir():
            continue
        pipeline = pipeline_dir.name
        for dataset_dir in sorted(pipeline_dir.iterdir()):
            if not dataset_dir.is_dir():
                continue
            dataset_name = dataset_dir.name
            text_rows, field_rows, n_docs = score_pipeline_dataset(args.run_id, pipeline, dataset_name, args.split)
 
            text_summary = summarize_text(text_rows, n_docs)
            field_summary = summarize_fields(field_rows, n_docs) if dataset_name in RESUME_DATASETS else {}
 
            print(f"\n=== {pipeline} / {dataset_name} (split={args.split or 'all'}) ===")
            print(f"  text : {text_summary}")
            if dataset_name in RESUME_DATASETS:
                print(f"  fields: {field_summary}")
 
            # Per-language breakdown -- pooled numbers hide a weak language behind
            # a good one on any mixed-language dataset (synthetic_cv's ar+en mix).
            languages = {r.get("language") for r in text_rows if r.get("language")}
            lang_summaries = {}
            if len(languages) > 1:
                for lang in sorted(languages):
                    lang_text_rows = [r for r in text_rows if r.get("language") == lang]
                    lang_field_rows = [r for r in field_rows if r.get("language") == lang]
                    lang_text_summary = summarize_text(lang_text_rows, len(lang_text_rows))
                    lang_field_summary = (summarize_fields(lang_field_rows, len(lang_field_rows))
                                           if dataset_name in RESUME_DATASETS else {})
                    lang_summaries[lang] = {"text": lang_text_summary, "fields": lang_field_summary}
                    print(f"  [{lang}] text : {lang_text_summary}")
                    if dataset_name in RESUME_DATASETS:
                        print(f"  [{lang}] fields: {lang_field_summary}")
 
            if text_rows and text_summary.get("diagnosis") not in (None, "usable"):
                worst = sorted(text_rows, key=lambda r: r["cer"], reverse=True)[:5]
                print(f"  worst 5 docs (inspect before drawing conclusions from the aggregate):")
                for r in worst:
                    print(f"    {r['doc_id']}: cer={r['cer']:.3f}")
 
            all_rows.append({"pipeline": pipeline, "dataset": dataset_name,
                              "split": args.split or "all", **text_summary,
                              **{f"lang_{lang}_{k}": v for lang, s in lang_summaries.items()
                                 for k, v in s["text"].items()},
                              **{f"field_{k}": v for k, v in field_summary.items()}})
 
    suffix = f"__{args.run_id}" + (f"__{args.split}" if args.split else "")
    df = pd.DataFrame(all_rows)
    df.to_csv(METRICS_DIR / f"summary{suffix}.csv", index=False)          # spreadsheet-pasteable view
    (METRICS_DIR / f"summary{suffix}.json").write_text(                    # full-fidelity, easy to reload in Python
        json.dumps(all_rows, indent=2, default=lambda o: None), encoding="utf-8")
    print(f"\nDone -> {METRICS_DIR}/summary{suffix}.csv and .json")
 
 
if __name__ == "__main__":
    main()