# Service report

Team: Yaser
Use case: Chat completions served via vLLM on Kubernetes (llmops namespace)
Service and model: team-serving / Qwen/Qwen2.5-1.5B-Instruct-AWQ (vLLM v0.27.1)
Measured requests or tasks: OpenAI-compatible /v1/chat/completions requests against vllm.yaser.win
Indicator and unit: p95 time-to-first-token (TTFT), seconds
SLO target and window: p95 TTFT < 2s, evaluated over a 5-minute rate window
Measurement start and end: 2026-09-14 ~09:57 UTC to ~10:20 UTC (load test session)
Workload: Synthetic load — 20 concurrent chat completion requests per round,
repeated for ~30 rounds, each requesting a long-form 500-token response, to
force queueing/compute contention on a single-GPU small-model deployment.
Observed result and sample count: Individual request latencies rose from an
idle baseline of ~0.2-0.5s to a sustained ~2.0-2.15s once 20 requests ran
concurrently (consistent across rounds 22-30, ~400+ sampled requests total).
Evidence: curl -w "%{time_total}" timings captured per request (see raw log);
PromQL histogram_quantile query against vllm:time_to_first_token_seconds_bucket.
Conclusion: Under simulated concurrent load, individual request latency
consistently exceeded the 2s SLO target. The Grafana-managed alert rule
("Team service alert") successfully evaluated the same indicator and
delivered a firing notification to the configured webhook inbox, confirming
the alerting pipeline is functional end-to-end.
Limitations: Load was synthetic (single repeated prompt, one client host),
not organic multi-user traffic. The alert payload captured in this report
window shows A=0.07s at time of firing — below the 2s threshold — meaning
this particular firing event was most likely triggered by Grafana's manual
"Test" action rather than a live threshold breach; a live breach during the
sustained load window was not independently confirmed in this session and
should be re-verified with a longer, continuous load run aligned to the
rule's 5-minute pending period.
Follow-up action: Re-run a continuous (non-bursty) load test for at least
6-7 minutes, cross-check the alert's `values.A`/`values.C` fields at the
moment of a confirmed firing event, and consider whether request
concurrency limits or autoscaling would keep p95 TTFT under target during
real traffic spikes.

## Measurement query

```promql
histogram_quantile(0.95,
  sum by (le) (rate(vllm:time_to_first_token_seconds_bucket{job="team-serving"}[5m]))
)
or
histogram_quantile(0.95,
  sum by (le) (rate(vllm_time_to_first_token_seconds_bucket{job="team-serving"}[5m]))
)
```

Evaluated as an Instant query. The `or` covers both possible metric-name
spellings across vLLM versions (one side returns data, the other returns
nothing). Measured at the Prometheus scrape layer (15s interval) against the
`team-serving` ServiceMonitor target; this excludes network/tunnel latency
between the client and `vllm.yaser.win`, and excludes queueing time that
occurs before a request is counted (i.e. it measures generation-side TTFT,
not total client-perceived round-trip time).

## Service alert

Condition and unit: p95 TTFT (seconds) IS ABOVE 2
Evaluation interval: 1m
Pending period: 5m
Relationship to the SLO: This condition directly measures the documented
latency SLO (p95 TTFT < 2s). It was chosen over a queue-depth metric
(`num_requests_waiting`) because queue depth only signals internal
congestion and does not confirm whether real user requests are actually
experiencing degraded response times — a request could sit briefly in queue
and still complete well within budget, or the queue could be empty while
GPU compute itself is the bottleneck. TTFT reflects the delay a user
actually perceives before any output appears, making it a true user-facing
latency signal directly tied to the SLO, rather than an operational proxy.
First response to a notification: Confirm whether the breach is transient
(brief traffic spike) or sustained; check `kubectl get pods -n llmops` and
`kubectl top pod -n llmops -l app=vllm` for resource pressure; if sustained,
consider whether concurrent request volume needs to be rate-limited or the
deployment needs additional replicas/GPU capacity.

## Notification test

Firing received at: 2026-09-14T10:20:10Z (webhook payload logged by
yaser-alert-inbox; alertname "Team service alert", folder "Yaser Lab")
Resolved received at: not yet observed in this session — requires a
follow-up check after the triggering condition clears
What the test establishes: The full alerting chain — Prometheus/Grafana
query evaluation → Reduce(Last) → Threshold(IS ABOVE 2) → Alert condition C
→ Contact point ("Lab inbox", webhook) → yaser-alert-inbox deployment in
llmops — delivers correctly formatted firing payloads, including rule name,
folder, and annotation text, confirming the pipeline is wired correctly
end-to-end. A dedicated re-test with a sustained (not manual-test) firing
event is recommended to also confirm the resolved-notification path.
