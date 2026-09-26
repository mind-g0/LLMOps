# Service report

Team: Salman
Use case: Monitor an LLM serving service and alert when end-to-end request latency exceeds the defined service target.
Service and model: llmops-serving / Qwen3.5-4B
Measured requests or tasks: LLM inference requests observed by the vLLM service metrics.
Indicator and unit: p95 end-to-end request latency in seconds.
SLO target and window: p95 end-to-end request latency <= 10 seconds, evaluated using a 24-hour measurement window.
Measurement start and end: 24-hour lookback window ending at the time of the Grafana measurement.
Workload: Existing inference traffic observed for /models/Qwen3.5-4B through the shared Prometheus data source.
Observed result and sample count: p95 end-to-end latency was 9 seconds; approximately 4 requests were observed in the 24-hour window.
Evidence: Grafana returned a finite value of 9 seconds for the p95 latency query, and the Team service alert evaluated successfully.
Conclusion: met
Limitations: Traffic was sparse, with approximately 4 observed requests in 24 hours, so the measurement provides limited evidence and the 10-second target is provisional.
Follow-up action: Collect more request samples under representative traffic and reassess the latency target and alert threshold.

## Measurement query

```promql
histogram_quantile(
  0.95,
  sum by (le) (
    rate(vllm:e2e_request_latency_seconds_bucket{model_name="/models/Qwen3.5-4B"}[24h])
  )
)
```

The query measures the p95 end-to-end request latency from the vLLM latency histogram for the Qwen3.5-4B model over a 24-hour lookback window. The 24-hour window was used because shorter 5-minute and 1-hour windows did not contain enough observations to produce a finite value. The measurement is taken from the Prometheus data source connected to Grafana and is filtered to the Qwen3.5-4B model. It excludes other model series.

## Service alert

Condition and unit: Alert when p95 end-to-end request latency is above 10 seconds.
Evaluation interval: 1 minute.
Pending period: 1 minute.
Relationship to the SLO: The alert threshold matches the proposed p95 latency SLO boundary of 10 seconds.
First response to a notification: Check the current latency metric, confirm the service and model are responding, inspect recent traffic and service health, and investigate the cause of increased latency.

## Notification test

Firing received at: 2026-09-14T08:55:05+00:00
Resolved received at: 2026-09-14T09:00:05+00:00
What the test establishes: The synthetic Lab notification test demonstrated that Grafana can evaluate an alert, send a firing notification to Lab inbox, and deliver a resolved notification to the alert-inbox webhook.