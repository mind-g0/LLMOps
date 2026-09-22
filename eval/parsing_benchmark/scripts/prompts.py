
CONTROL_PROMPT = (
    "Transcribe all visible text in this image in natural reading order. "
    "Output only the transcription."
)
 
# ---------------------------------------------------------------------------
# Canonical / trained prompts — verbatim from each model's own card.
# ---------------------------------------------------------------------------
 

QIANFAN_NATIVE_PROMPT = "Parse this document to Markdown."
GLM_NATIVE_PROMPT = "Text Recognition:"
 
# ---------------------------------------------------------------------------
# Custom, dataset-shaped prompts — used only for models that actually follow
# free-form instructions well (qwen3_vl always; qianfan/glm also get a
# "resume" variant to A/B against their minimal native prompt, since it's
# an open question whether their instruction-following is strong enough to
# benefit without going off-distribution).
# ---------------------------------------------------------------------------
 
ARABIC_DOC_PROMPT = """Transcribe this document image into plain text.
 
- Transcribe every visible character exactly as it appears, in natural reading order. For right-to-left text, read right to left.
- Include all headers, footers, page numbers, captions, and marginal notes.
- Keep numbers, dates and punctuation exactly as printed. Do not convert between Arabic-Indic and Western digits.
- If the page mixes scripts, transcribe each part in its original script. Do not translate.
- Transcribe only what is visible. Do not infer, complete or correct the text.
- Do not repeat any line. If a region is illegible, write [illegible] once and continue.
- Output only the transcription, with no preamble or commentary."""
 
RESUME_MULTICOL_PROMPT = """Transcribe this resume image into plain text.
 
- First determine the column layout. If the page has multiple columns or a sidebar, transcribe each column completely, top to bottom, before moving to the next. Do not interleave columns.
- Include every region: header block, sidebar, skills lists, contact details, dates, footers. Sidebar content is part of the document and must not be skipped.
- Keep emails, phone numbers, URLs and dates exactly as printed. Do not reformat them.
- Transcribe only what is visible. Do not infer or complete missing information.
- Do not repeat any line. If a region is illegible, write [illegible] once and continue.
- Output only the transcription, with no preamble or commentary."""
 
# ---------------------------------------------------------------------------
# Which task-shaped prompt applies to which dataset — explicit mapping
# instead of substring-matching the dataset name (the old "resume" in
# dataset.lower() check silently missed "synthetic_cv").
# ---------------------------------------------------------------------------
 
DATASET_TASK = {
    "resume_dataset_hf": "resume",
    "synthetic_cv": "resume",
}
 
TASK_PROMPT = {"arabic_doc": ARABIC_DOC_PROMPT, "resume": RESUME_MULTICOL_PROMPT}
 
PROMPTS = {
    "qianfan_ocr":   {"native": QIANFAN_NATIVE_PROMPT, "control": CONTROL_PROMPT},
    "glm_ocr":       {"native": GLM_NATIVE_PROMPT,     "control": CONTROL_PROMPT},
    "qwen3_vl":      {"control": CONTROL_PROMPT},  
    "qwen3_5_4b":    {"control": CONTROL_PROMPT},
    "claude_haiku":  {"control": CONTROL_PROMPT},  
}
 
# Models allowed to use the task-shaped ("resume") variant as
# an alternative to their bare native prompt, for the native-vs-task A/B.
TASK_VARIANT_ALLOWED = {"qianfan_ocr", "glm_ocr", "qwen3_vl", "qwen3_5_4b", "claude_haiku"}
 
# General instruction-following models with no single trained "native"
# prompt — their "native" request always routes to the task-shaped prompt.
# Add a model here (not a new if-check) when it's this kind, not an
# OCR-specialized fine-tune with its own canonical instruction.
NO_FIXED_NATIVE_PROMPT = {"qwen3_vl", "qwen3_5_4b", "claude_haiku"}
 
 
def get_prompt(pipeline: str, variant: str, dataset: str) -> str:
    """variant: 'native' | 'control' | 'task'.
    'task' resolves via DATASET_TASK — explicit per-dataset, not a string
    match on the dataset name."""
    table = PROMPTS.get(pipeline)
    if table is None:
        raise KeyError(f"No prompt registered for {pipeline!r}")
 
    if variant == "task":
        if pipeline not in TASK_VARIANT_ALLOWED:
            raise KeyError(f"{pipeline!r} is not in TASK_VARIANT_ALLOWED — "
                            f"its native prompt is the trained instruction, don't override it.")
        task = DATASET_TASK.get(dataset)
        if task is None:
            raise KeyError(f"No DATASET_TASK entry for {dataset!r} — add one before running.")
        return TASK_PROMPT[task]
 
    if pipeline in NO_FIXED_NATIVE_PROMPT and variant == "native":
        return get_prompt(pipeline, "task", dataset)
 
    if variant not in table:
        raise KeyError(f"{pipeline!r} has no variant {variant!r}; have {sorted(table)} (+ 'task' if allowed)")
    return table[variant]