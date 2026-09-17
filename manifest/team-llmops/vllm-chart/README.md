# vLLM Serving — Team LLMOps

Helm chart for deploying vLLM-based LLM serving on Kubernetes with GPU acceleration. Supports OpenAI-compatible API, tool calling, and monitoring via Prometheus/Grafana.

## Prerequisites

- Kubernetes cluster with GPU nodes (NVIDIA RTX A6000 or similar)
- NVIDIA GPU operator installed (`nvidia.com/gpu` allocatable)
- [Helm 3+](https://helm.sh)

## Quick Start

### 1. Create the API key secret

The chart expects a Kubernetes secret named `serving-keys` with an `api-key` field. Create it before installing:

```bash
kubectl create ns llmops 2>/dev/null
kubectl create secret generic serving-keys -n llmops \
  --from-literal=api-key='your-vllm-api-key-here'
```

Or from an env file:

```bash
echo "api-key=your-vllm-api-key-here" > serving-keys.env
kubectl create secret generic serving-keys -n llmops --from-env-file=serving-keys.env
```

To update the key later:

```bash
kubectl delete secret -n llmops serving-keys
kubectl create secret generic serving-keys -n llmops \
  --from-literal=api-key='your-new-key'
```

### 2. Deploy the chart

```bash
cd /home/nassir/LLMOps/manifest/team-llmops/vllm-chart

helm install llmops ./ -n llmops
```

Or upgrade if already installed:

```bash
helm upgrade llmops ./ -n llmops
```

### 3. Check status

```bash
kubectl get pods -n llmops -w
kubectl logs -n llmops deploy/llmops-serving -f
```

## Configuration

All settings are in `values.yaml`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `image` | `vllm/vllm-openai:v0.29.0` | vLLM Docker image |
| `model.id` | `/models/Qwen3.5-4B` | Path to model on the host |
| `model.dtype` | `half` | Model precision |
| `model.maxModelLen` | `131072` | Maximum context length |
| `model.gpuMemoryUtilization` | `0.9` | Fraction of VRAM to use (0.0-1.0) |
| `model.autoToolChoice` | `true` | Enable auto tool calling |
| `model.toolCallParser` | `hermes` | Tool call format parser |
| `model.prefixCaching` | `true` | Enable KV cache prefix reuse |
| `resources.requests.nvidia.com/gpu` | `1` | GPUs per pod |
| `resources.requests.cpu` | `4` | CPU cores |
| `resources.requests.memory` | `16Gi` | RAM |
| `service.port` | `8000` | Container port |
| `modelVolume.hostPath` | `/home/nassir/models/Qwen3.5-4B` | Host path to model weights |
| `modelVolume.mountPath` | `/models/Qwen3.5-4B` | Mount path inside container |
| `modelCache.hostPath` | `/var/lib/hf-cache` | HuggingFace cache on host |

### Model paths

Models are mounted into the container via hostPath volumes. The `model.id` arg must match the `mountPath`. Example mapping:

```yaml
modelVolume:
  hostPath: /home/nassir/models/Qwen3.5-4B
  mountPath: /models/Qwen3.5-4B

model:
  id: /models/Qwen3.5-4B
```

### Switching models

To deploy a different model (e.g. Qwen3.8-27B-FP8):

```yaml
modelVolume:
  hostPath: /home/nassir/models/Qwen3.8-27B-FP8
  mountPath: /models/Qwen3.8-27B-FP8

model:
  id: /models/Qwen3.8-27B-FP8
  # dtype: half is fine for FP8-quantized models
```

Then `helm upgrade llmops ./ -n llmops` to apply.

## Storage

The chart doesn't manage model storage — model weights are expected to exist on the node at the `modelVolume.hostPath`. Models are cloned from HuggingFace:

```bash
# Using HuggingFace CLI
huggingface-cli download Qwen/Qwen3.5-4B --local-dir /home/nassir/models/Qwen3.5-4B

# Or using git LFS
cd /home/nassir/models
GIT_LFS_SKIP_SMUDGE=1 git clone https://huggingface.co/Qwen/Qwen3.5-4B
cd Qwen3.5-4B
git lfs pull
```

## Monitoring

The `monetor-stack` in the parent directory provides Prometheus + Grafana for the vLLM serving. vLLM exposes metrics at `/metrics` on port 8000, scraped by Prometheus at `llmops-serving:8000`.

## Notes

- The `serving-keys` secret is managed outside Helm — the chart no longer includes a Secret template. Create it manually before deploying.
- vLLM 0.29.0 supports prefix caching (`--enable-prefix-caching`), auto tool choice, and hermes tool parser.
- Context length (`maxModelLen`) of 131072 requires enough VRAM for KV cache. Reduce if OOMs occur.