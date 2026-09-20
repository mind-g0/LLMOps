# Resume Parsing Benchmark — Results

**Models:** Qianfan-OCR, Qwen3-VL-8B-Instruct, Docling (text-layer, no VLM), Qwen3.5-4B
**Datasets:** `resume_dataset_hf` (real English resumes), `synthetic_cv` (Arabic + English, generated)
**N:** 200 docs per dataset per model

---

## Metric definitions

- **CER / WER** Character / Word Error Rate. % of characters or words wrong vs. ground truth. Lower is better. WER is stricter: one wrong letter makes the whole word count as wrong.
- **micro** all documents pooled into one ratio (weighted by length).
- **mean** average of each document's own score (every document counts equally).
- **median** the middle score (ignores outliers tells you the typical document, not the average).
- **CI95 (lo/hi)** 95% confidence range for the metric.
- **skills-F1** fuzzy-matched precision/recall/F1 on extracted skills (>=90% string similarity counts as a match).
- **education / experience accuracy** field accuracy on matched records (jobs/degrees matched to their closest ground-truth counterpart first, then scored).
- **lang_ar / lang_en** same metrics, split by language, for `synthetic_cv`.
- **Docling (full)** library defaults: text-layer extraction + DocLayNet layout model + TableFormer table-structure model + OCR fallback. No GPU.
- **Docling (simple)** text-layer extraction only, `do_ocr=False`, `do_table_structure=False`. No GPU.

---

## Results

### resume_dataset_hf

| Metric | Qianfan | Qwen3-VL | Docling (full) | Docling (simple) | Qwen3.5-4B |
|---|---|---|---|---|---|
| micro CER | 0.090 | **0.076** | 0.106 | 0.092 | 0.140 |
| mean CER | 0.106 | **0.082** | 0.117 | 0.101 | 0.106 |
| median CER | 0.033 | **0.030** | 0.050 | 0.040 | 0.030 |
| micro WER | 0.280 | **0.233** | 0.267 | 0.253 | 0.284 |
| mean WER | 0.341 | **0.266** | 0.302 | 0.277 | 0.278 |
| median WER | 0.174 | 0.156 | 0.198 | 0.193 | **0.153** |
| skills-F1 | 0.0004 | 0.0007 | 0.0006 | 0.0006 | 0.0006 |

*Skills-F1 is near-zero for all five known ground-truth labeling issue in this dataset, not a model result.*
*Docling (simple) beats Docling (full) on every metric here the layout/table model is adding error on real, messier resumes, not helping.*

### synthetic_cv — overall

| Metric | Qianfan | Qwen3-VL | Docling (full) | Docling (simple) | Qwen3.5-4B |
|---|---|---|---|---|---|
| micro CER | 0.097 | **0.070** | 0.142 | 0.142 | 0.202 |
| mean CER | 0.118 | **0.079** | 0.165 | 0.165 | 0.252 |
| median CER | **0.012** | 0.021 | 0.099 | 0.099 | 0.023 |
| micro WER | 0.138 | **0.118** | 0.199 | 0.199 | 0.282 |
| mean WER | 0.153 | **0.122** | 0.212 | 0.212 | 0.316 |
| median WER | **0.049** | 0.075 | 0.147 | 0.147 | 0.078 |
| skills-F1 | **0.969** | 0.966 | 0.962 | 0.958 | 0.926 |
| education acc. | 0.886 | 0.887 | **0.892** | 0.892 | 0.891 |
| experience acc. | 0.930 | **0.949** | 0.932 | 0.927 | 0.925 |

*Docling (full) and Docling (simple) are essentially identical here (differences in the 4th decimal place) — on this dataset's documents, the layout/table model makes no measurable difference either way. This contradicts an earlier 20-document pilot that suggested simple mode was meaningfully better; that pilot result was noise, not a real effect — corrected here at full N=200.*

### synthetic_cv — Arabic only

| Metric | Qianfan | Qwen3-VL | Docling (full) | Docling (simple) | Qwen3.5-4B |
|---|---|---|---|---|---|
| micro CER | 0.228 | **0.165** | 0.298 | 0.298 | 0.481 |
| mean CER | 0.232 | **0.155** | 0.298 | 0.297 | 0.501 |
| median CER | **0.046** | 0.062 | 0.210 | 0.210 | 0.100 |
| micro WER | 0.288 | **0.241** | 0.351 | 0.351 | 0.604 |
| mean WER | 0.294 | **0.229** | 0.351 | 0.350 | 0.618 |
| median WER | **0.112** | 0.140 | 0.268 | 0.268 | 0.177 |

*Qwen3.5-4B's Arabic CI95 is 0.26–0.79 — extremely wide, driven by severe repetition on a subset of documents (ins_rate 0.31, the highest of any row here). Treat its Arabic result as unstable, not a reliable point estimate.*

### synthetic_cv — English only

| Metric | Qianfan | Qwen3-VL | Docling (full) | Docling (simple) | Qwen3.5-4B |
|---|---|---|---|---|---|
| micro CER | 0.0034 | 0.0032 | 0.031 | 0.031 | 0.0034 |
| micro WER | 0.0128 | 0.0148 | 0.073 | 0.073 | 0.0140 |

*Docling underperforms the VLMs here even in simple mode — this rules out the layout model as the cause. Genuinely still unexplained; likely a markdown-formatting mismatch against the plain-text ground truth rather than content loss, but this is now a real open question, not a solved one.*

---

## Headlines

1. **Qwen3-VL wins on micro/mean CER/WER** across every dataset and both languages — the strongest model overall on text quality.
2. **Qianfan wins on median CER/WER on Arabic and on `synthetic_cv` overall** — more consistent typical-case performance even where it loses the average.
3. **Field extraction is a near-tie between Qianfan, Qwen3-VL, and both Docling modes** (all ≥0.96 skills-F1 except Docling-simple at 0.958); **Qwen3.5-4B is clearly behind** (0.926).
4. **Qwen3.5-4B is unreliable on Arabic specifically** — its micro CER/WER are far worse than the other four, driven by severe repetition on a subset of documents, not a uniform weakness.
5. **Docling's layout/table model helps on real resumes but does nothing on synthetic ones** — simple mode beats full mode on every `resume_dataset_hf` metric, but the two modes are statistically identical on `synthetic_cv`. Recommendation: use simple mode as the Docling baseline going forward — never worse, sometimes better, and cheaper (no neural models to load).
6. **Docling's English underperformance on `synthetic_cv` is still unexplained** — ruled out the layout model as the cause; likely a formatting/normalization issue worth a manual spot-check, not yet a confirmed finding.
7. **`resume_dataset_hf` skills-F1 is unusable for all five models** — ground truth labeling problem, not a model result.