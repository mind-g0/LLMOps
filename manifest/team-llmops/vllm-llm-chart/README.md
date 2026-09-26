# vLLM LLM Serving - Team LLMOps

Helm chart for deploying vLLM-based LLM serving on Kubernetes with GPU acceleration. Supports OpenAI-compatible API, tool calling, and monitoring via Prometheus/Grafana.

## Prerequisites

- Kubernetes cluster with GPU nodes
- NVIDIA GPU operator installed (nvidia.com/gpu allocatable)
- Helm 3+

## Quick Start

### 1. Generate and create the API key secret

The chart expects a Kubernetes secret named serving-keys with an api-key field.

Generate a secure random key:

```bash
API_KEY=$(openssl rand -hex 32)
echo "$API_KEY"
```

Create the secret:

```bash
kubectl create ns llmops 2>/dev/null
kubectl create secret generic serving-keys -n llmops --from-literal=api-key="$API_KEY"
```

### 2. Deploy the chart

```bash
cd /home/nassir/LLMOps/manifest/team-llmops/vllm-llm-chart
helm install llmops-llm ./ -n llmops
```

Or upgrade:

```bash
helm upgrade llmops-llm ./ -n llmops
```

### 3. Test it

```bash
KEY=$(kubectl get secret -n llmops serving-keys -o jsonpath="{.data.api-key}" | base64 -d)
curl -X POST http://<clusterip>:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $KEY" \
  -d '{"model":"/models/Qwen3.5-9B","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'
```

## Configuration

All settings in values.yaml. Key parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `apiKeySecret.name` | `serving-keys` | Secret containing the API key |
| `apiKeySecret.key` | `api-key` | Key name inside the secret |
| `image` | `vllm/vllm-openai:v0.27.1` | vLLM Docker image |
| `model.id` | `/models/Qwen3.5-9B` | Model path matching mountPath |
| `model.dtype` | `auto` | Model precision |
| `model.maxModelLen` | `64000` | Maximum context length |
| `model.gpuMemoryUtilization` | `0.5` | Fraction of VRAM to use |
| `service.port` | `8000` | Container port |
| `resources.requests.nvidia.com/gpu` | `1` | GPUs per pod |
| `resources.requests.cpu` | `4` | CPU cores |
| `resources.requests.memory` | `6Gi` | RAM |

## Managing the API key

### View the current key

```bash
kubectl get secret -n llmops serving-keys -o jsonpath="{.data.api-key}" | base64 -d
```

### Update the key without downtime

```bash
NEW_KEY=$(openssl rand -hex 32)
kubectl patch secret -n llmops serving-keys \
  -p '{"data":{"api-key":"'$(echo -n "$NEW_KEY" | base64)'"}}'
kubectl rollout restart -n llmops deploy/llmops-llm-serving
```

### Rotate keys with zero downtime

1. Create a second secret with the new key
2. Update `apiKeySecret.name` in values.yaml to the new secret
3. Run `helm upgrade llmops-llm ./ -n llmops` to roll pods
4. Delete the old secret once all pods are healthy

## Model paths

Models are mounted via hostPath volumes. `model.id` must match `mountPath`:

```yaml
modelVolume:
  hostPath: /home/nassir/models/Qwen3.5-9B
  mountPath: /models/Qwen3.5-9B
model:
  id: /models/Qwen3.5-9B
```

### Switching models

```yaml
modelVolume:
  hostPath: /home/nassir/models/NEW-MODEL
  mountPath: /models/NEW-MODEL
model:
  id: /models/NEW-MODEL
```

Then `helm upgrade llmops-llm ./ -n llmops` to apply.

## Storage

Model weights exist on the node at `modelVolume.hostPath`. Clone from HuggingFace:

```bash
huggingface-cli download Qwen/Qwen3.5-9B --local-dir /home/nassir/models/Qwen3.5-9B
```

## Monitoring

Prometheus scrapes `/metrics` on port 8000. Grafana dashboards in `monetor-stack`.

## Notes

- `serving-keys` is managed outside Helm -- create it before first deploy.
- The chart references the secret via `apiKeySecret` in values.yaml.
- vLLM enforces auth via `VLLM_API_KEY` env var. No valid Bearer token = 401.
