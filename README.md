# otel-instrumented-service

A small HTTP service that demonstrates the **three pillars of observability** in
one place:

- **Traces** — OpenTelemetry spans (with nested child spans for downstream calls)
- **Metrics** — Prometheus **RED** metrics (Rate, Errors, Duration)
- **Logs** — structured JSON logs, correlated to traces via trace/span ids

It's designed to pair with a monitoring stack (e.g. Prometheus + an OTLP
collector): it exposes `/metrics` for scraping and can export spans over OTLP.

## Endpoints

| Endpoint    | Purpose                                             |
| ----------- | --------------------------------------------------- |
| `/healthz`  | Liveness                                            |
| `/readyz`   | Readiness                                           |
| `/metrics`  | Prometheus exposition (RED metrics)                 |
| `/work`     | Simulated traced unit of work with variable latency |
| `/error`    | Always 500 — exercises error metrics / SLO alerts   |

## Metrics exposed (RED)

```
http_requests_total{method,path,code}          # Rate + Errors
http_request_duration_seconds{method,path}      # Duration (histogram)
http_requests_in_flight                         # concurrency gauge
```

These are exactly the SLIs a burn-rate SLO alert consumes (e.g. error ratio =
5xx rate / total rate), so this service is a natural traffic generator for a
Prometheus-based SLO setup.

## Run locally

```bash
pip install -e .
otel-service                      # traces exporter defaults to "none"
# or with span export to stdout:
OTEL_EXPORTER=console otel-service

curl localhost:8080/work
curl localhost:8080/error
curl localhost:8080/metrics
```

Structured log line (correlated to a trace):

```json
{"timestamp":"...","level":"info","logger":"otel_service","message":"request completed",
 "method":"GET","path":"/work","status":200,"duration_ms":18.4,
 "trace_id":"3f2b...","span_id":"a1c9..."}
```

## Traces

`configure_tracing(exporter=...)` supports:

- `none` — spans created but not exported (default; zero external dependency)
- `console` — spans printed to stdout
- `otlp` — export to an OTLP collector (`pip install ".[otlp]"`)

## Kubernetes

`k8s/deployment.yaml` runs the service non-root with liveness/readiness probes
and the `prometheus.io/scrape` annotations that a cluster Prometheus uses to
discover and scrape `/metrics`.

## Development

```bash
pip install -e ".[dev]"
ruff check .
pytest -q
```

CI runs `ruff`, `pytest` (Python 3.10–3.12), and a Docker build on every push.

## Note

A personal, illustrative project for demonstrating observability instrumentation
patterns end to end.
