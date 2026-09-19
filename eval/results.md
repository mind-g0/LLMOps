# Resume Parsing Benchmark — Results

**Models:** Qianfan-OCR vs. Qwen3-VL-8B-Instruct
**Datasets:** `resume_dataset_hf` (real English resumes), `synthetic_cv` (Mix Arabic and English, generated)
**N:** 200 docs per dataset per model

---

## Metric definitions

- **CER / WER** — Character / Word Error Rate. % of characters or words wrong vs. ground truth. Lower is better. WER is stricter: one wrong letter makes the whole word count as wrong.
- **micro** — all documents pooled into one ratio (weighted by length).
- **mean** — average of each document's own score (every document counts equally).
- **median** — the middle score (ignores outliers — tells you the typical document, not the average).
- **CI95 (lo/hi)** — 95% confidence range for the metric.
- **skills-F1** — fuzzy-matched precision/recall/F1 on extracted skills (>=90% string similarity counts as a match).
- **education / experience accuracy** — field accuracy on matched records (jobs/degrees matched to their closest ground-truth counterpart first, then scored).
- **lang_ar / lang_en** — same metrics, split by language, for `synthetic_cv`.

---

## Results

### resume_dataset_hf

| Metric | Qianfan | Qwen3-VL |
|---|---|---|
| micro CER | 0.090 | **0.076** |
| mean CER | 0.106 | **0.082** |
| median CER | 0.033 | **0.030** |
| micro WER | 0.280 | **0.233** |
| mean WER | 0.341 | **0.266** |
| median WER | 0.174 | **0.156** |
| skills-F1 | 0.0004 | 0.0007 |

*Skills-F1 is near-zero for both models -- known ground-truth labeling issue in this dataset, not a model result.*

### synthetic_cv — overall

| Metric | Qianfan | Qwen3-VL |
|---|---|---|
| micro CER | 0.097 | **0.070** |
| mean CER | 0.118 | **0.079** |
| median CER | **0.012** | 0.021 |
| micro WER | 0.138 | **0.118** |
| mean WER | 0.153 | **0.122** |
| median WER | **0.049** | 0.075 |
| skills-F1 | 0.969 | 0.966 |
| education acc. | 0.886 | 0.887 |
| experience acc. | 0.930 | **0.949** |

### synthetic_cv — Arabic only

| Metric | Qianfan | Qwen3-VL |
|---|---|---|
| micro CER | 0.228 | **0.165** |
| mean CER | 0.232 | **0.155** |
| median CER | **0.046** | 0.062 |
| micro WER | 0.288 | **0.241** |
| mean WER | 0.294 | **0.229** |
| median WER | **0.112** | 0.140 |

### synthetic_cv — English only

Both models near-perfect: ~0.3% CER, ~1.3-1.5% WER, essentially tied.

---

## Headlines

1. **Qwen3-VL wins on micro and mean CER/WER** across every dataset and both languages.
2. **Qianfan wins on median CER/WER on Arabic** -- more consistent typical-case performance, even though Qwen wins the average.
3. **Field extraction (skills, education, experience) is a near-tie** on trustworthy ground truth (`synthetic_cv`), both >0.96 skills-F1.
4. **`resume_dataset_hf` skills-F1 is not usable** for either model -- ground truth labeling problem, not a model result.
