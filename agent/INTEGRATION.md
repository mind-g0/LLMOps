# LLMOps Integration Agent — Full Audit & Fix Log

**Server:** `aidc-t03` (1x RTX A6000 48GB, K3s cluster)  
**Repo:** `/home/nassir/LLMOps`  
**Agent:** `/home/nassir/LLMOps/agent/`  
**Charts:** `/home/nassir/LLMOps/manifest/team-llmops/`  
**Date:** 2026-09-22

---

## 1. Logic Bug — Empty Job Requirements Caused Infinite Loop

### Symptom
```
[11:33:11] WARNING | [cv_id] job 'fc64e830-...' not found in Qdrant — sync it first
```
Repeated every 30 seconds. Same CV picked up every poll cycle because the agent returned early without PATCHing results, so the CV stayed `needs_human_review` forever.

### Root Cause (commit 7fd0460)
All 3 jobs on the server had `"requirements": []` — the required_skills field was empty. The old guard:

```python
# OLD (7fd0459 and earlier)
if not job or not job[0].required_skills:
```

Rejected every job because `[].required_skills` was falsy. The agent synced jobs to Qdrant correctly, then immediately rejected them at the process_one gate, returned early, never PATCHed the CV → infinite loop.

### Fix
Changed to:
```python
# NEW (7fd0460)
if not job:
```
Now only fails when the job literally doesn't exist in Qdrant. Also fixed the retriever node:
```python
# OLD
if not req.required_skills:
# NEW
if not req.required_skills and not chunks:
```

---

## 2. Python Version Conflict (3.10 Compatibility)

### Symptom
```python
ImportError: cannot import name 'NDArray' from partially initialized module 'numpy._typing'
```
On Python 3.10, dspy's lazy import wrapper conflicts with numpy's internal imports when qdrant-client triggers `numpy.typing`.

### Fix
Added at top of `agent/main.py`:
```python
import numpy as np  # must load before dspy to avoid circular import
```
Installed numpy pinned to `<2.0` for Python 3.10 compatibility.

---

## 3. GPU Time-Slicing — Running Two Models on One GPU

### Challenge
Only 1 physical RTX A6000 (48GB) detected on the server. Both LLM (Qwen3.5-9B) and OCR (Qwen3-VL-8B) needed to coexist.

### Solution
Two-part fix:

#### 3a. NVIDIA Device Plugin Time-Slicing (already configured)
`manifest/team-llmops/gpu-share/nvidia-device-plugin-config.yaml` splits the single GPU into 2 time-sliced replicas:
```yaml
sharing:
  timeSlicing:
    replicas: 2
```

#### 3b. FP8 Quantization for LLM → Fits Both in 48GB
Downloaded `RedHatAI/Qwen3.5-9B-FP8-dynamic` (compressed-tensors format, 14GB vs 19GB BF16). Final VRAM allocation:

| Service | Model | Weights | gpuMemoryUtilization | VRAM |
|---------|-------|---------|---------------------|------|
| LLM | Qwen3.5-9B FP8 | ~9GB | 0.35 (16.8GB) | 15.7GB |
| OCR | Qwen3-VL-8B FP16 | ~16GB | 0.55 (26.4GB) | 23.5GB |
| **Total** | | | | **39.2GB / 48GB** |

---

## 4. Chart Values Fixed

### `vllm-llm-chart/values.yaml`
```yaml
model:
  id: /models/Qwen3.5-9B-FP8
  # quantization auto-detected from config.json
  dtype: auto
  maxModelLen: 8192           # was 64000 — 64k context overflows 1 GPU
  gpuMemoryUtilization: "0.35"  # was 0.5
  maxNumSeqs: 32

resources:
  requests:
    cpu: "2"                  # was 4
    memory: 16Gi              # was 6Gi — 6Gi caused OOM during model load
    nvidia.com/gpu: 1

modelVolume:
  hostPath: /home/nassir/models/Qwen3.5-9B-FP8
  mountPath: /models/Qwen3.5-9B-FP8

startupProbe:
  failureThreshold: 120       # was 60 — model loading + torch.compile needs 2-5min
```

### `vllm-OCR-chart/values.yaml`
```yaml
model:
  id: /models/Qwen3-VL-8B-Instruct
  dtype: auto
  maxModelLen: 16384
  gpuMemoryUtilization: "0.55"  # was 0.45; more room for VLM quality
  maxNumSeqs: 4

resources:
  requests:
    memory: 12Gi              # was 8Gi

modelVolume:
  hostPath: /home/nassir/models/Qwen3-VL-8B-Instruct
  mountPath: /models/Qwen3-VL-8B-Instruct
```

---

## 5. Infinite Loop Fix — On-Demand Job Sync

### Symptom
New CV + job pair created after agent start → job not in Qdrant → agent returns early → CV never gets PATCHed → picked up every poll cycle → infinite loop.

### Three Changes

#### 5a. `sync_all_jobs()` moved inside the loop
```python
# OLD: called once at startup
sync_all_jobs()
while True:
    ...

# NEW: called every poll cycle
while True:
    sync_all_jobs()
    ...
```

#### 5b. New `_sync_job()` helper + on-demand fetch in `process_one()`
```python
if not job:
    log.info(f"job '{job_id}' not in Qdrant — fetching on demand")
    if _sync_job(job_id):
        job = store.get_job(job_id)
if not job:
    log.warning(f"job '{job_id}' could not be synced — skipping")
    return
```
Fetches a single job's `/spec` endpoint, builds the `JobRequirement`, upserts to Qdrant, then retries.

#### 5c. Every path produces a PATCH
The early `return` on "not found" was replaced with on-demand sync + retry. Every code path now saves the CV back to the backend (even as `needs_human_review` if the job genuinely can't be found), so the CV exits the pending queue permanently.

---

## 6. Streaming Disabled (Prevents 502 Errors)

**File:** `agent/dspy_setup.py`  
**Env var:** `GATEWAY_STREAM=0`

With `GATEWAY_STREAM=1`, every LLM request set `"stream": True` in the payload. The gateway tried SSE streaming to the agent, which failed intermittently with 502. Disabling streaming returns the complete response in one HTTP round-trip, eliminating the fragile stream-chunk parsing path.

---

## 7. Disk Pressure Resolved

### Symptom
All pods evicted with:
```
The node was low on resource: ephemeral-storage. Threshold quantity: 10512078185
```
The 9GB vLLM image pull + model loading spiked ephemeral-storage usage past the kubelet hard eviction threshold (~10GB). Also the `/data` drive was at 95% (11GB free).

### Cleanup performed
| Action | Space freed |
|--------|-------------|
| Removed duplicate bge-m3 at `/home/nassir/models/hf/` | 4.3G |
| Deleted stale HF cache (downloaded models not in use: Qwen3-14B, Qwen3.5-4B, Qwen3.8-27B, Qianfan-OCR, etc.) | ~4G |
| Deleted old BF16 Qwen3.5-9B (19G → replaced by 14G FP8) | 5G |
| Removed pip cache | 3.2G |
| **Total freed** | **~16G** |

**Current state:** `/data` 69% full (59G free), DiskPressure False.

---

## 8. Current Running State

```
llmops-llm-serving   1/1  Running  11m  10.43.233.104:8000  (Qwen3.5-9B-FP8)
llmops-ocr-serving   1/1  Running  11m  10.43.136.184:8001  (Qwen3-VL-8B-FP16)
```

Tested: both endpoints respond to `/v1/chat/completions`.

---

## 9. Key Files

| File | Purpose |
|------|---------|
| `manifest/team-llmops/vllm-llm-chart/values.yaml` | LLM serving config (FP8) |
| `manifest/team-llmops/vllm-ocr-chart/values.yaml` | OCR serving config (FP16) |
| `manifest/team-llmops/gpu-share/nvidia-device-plugin-config.yaml` | GPU time-slicing config |
| `agent/main.py` | CV review agent (on-demand sync, streaming off) |
| `agent/dspy_setup.py` | DSPy LM wrapper (GATEWAY_STREAM support) |
| `agent/.env` | Agent env (GATEWAY_STREAM=0) |
| `app/gateway.py` | Backend gateway (timeout bumped to 300s) |

---

## 10. Restarting After Git Pull

```bash
# Kill old process
pkill -f "uvicorn app.main"

# Redeploy agent — scale up to force a fresh start (image is cached)
kubectl rollout restart -n llmops deploy/llmops-llm-serving
kubectl rollout restart -n llmops deploy/llmops-ocr-serving

# Run agent manually
cd /home/nassir/LLMOps/agent
source ../.venv/bin/activate
python3 main.py --once

# Or as daemon
python3 main.py --watch --interval 30
```

---

## 11. Adding New CVs / Jobs

Jobs and CVs created via the backend API are automatically handled:
1. New job → `sync_all_jobs()` at next poll picks it up
2. New CV referencing that job → `_sync_job(job_id)` fetches and upserts it on-demand in `process_one()`
3. No restart needed.

---

## 12. Known Constraints

- **Single GPU:** Only 1 RTX A6000 (48GB) detected. Time-slicing allows both models to share, but total VRAM (39GB/48GB) is near capacity. Adding a third model will OOM.
- **FP8 LLM:** `RedHatAI/Qwen3.5-9B-FP8-dynamic` uses `compressed-tensors` format (auto-detected by vLLM). The `model_mtp.safetensors` (MTP head) is loaded but unused — vLLM ignores it.
- **OCR restart:** OCR restarted once during initial load (concurrent GPU pressure). Stable after both models settle.
- **Disk:** `/data` is 69% full. The vLLM image (9GB) is cached, but a future image update will spike disk usage. Keep 15GB+ free headroom.