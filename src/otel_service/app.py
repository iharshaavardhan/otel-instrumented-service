"""Flask application instrumented with traces, RED metrics, and structured logs.

Endpoints:
  GET  /healthz     liveness
  GET  /readyz      readiness
  GET  /metrics     Prometheus exposition
  GET  /work        simulated unit of work (traced, variable latency)
  GET  /error       always returns 500 (to exercise error metrics/SLOs)
"""

from __future__ import annotations

import os
import random
import time

from flask import Flask, Response, request
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .logging_config import get_logger
from .metrics import Metrics
from .tracing import configure_tracing, current_trace_ids


def create_app(exporter: str = "none") -> Flask:
    """Application factory. `exporter` selects the OTel span exporter."""
    app = Flask(__name__)
    app.config["METRICS"] = Metrics()
    app.config["TRACER"] = configure_tracing(exporter=exporter)
    log = get_logger()

    metrics: Metrics = app.config["METRICS"]
    tracer = app.config["TRACER"]

    @app.before_request
    def _start_timer() -> None:
        request.environ["_start_time"] = time.perf_counter()
        metrics.in_flight.inc()

    @app.after_request
    def _record(response: Response) -> Response:
        start = request.environ.get("_start_time")
        duration = time.perf_counter() - start if start is not None else 0.0
        metrics.in_flight.dec()
        # Use the URL rule as the path label to avoid high-cardinality raw paths.
        path = request.url_rule.rule if request.url_rule else "unmatched"
        metrics.observe(request.method, path, response.status_code, duration)

        trace_id, span_id = current_trace_ids()
        log.info(
            "request completed",
            extra={
                "method": request.method,
                "path": path,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
                "trace_id": trace_id,
                "span_id": span_id,
            },
        )
        return response

    @app.get("/healthz")
    def healthz() -> tuple[dict, int]:
        return {"status": "alive"}, 200

    @app.get("/readyz")
    def readyz() -> tuple[dict, int]:
        return {"status": "ready"}, 200

    @app.get("/metrics")
    def metrics_endpoint() -> Response:
        return Response(generate_latest(metrics.registry), mimetype=CONTENT_TYPE_LATEST)

    @app.get("/work")
    def work() -> tuple[dict, int]:
        # A child span models a downstream dependency call.
        with tracer.start_as_current_span("do-work") as span:
            with tracer.start_as_current_span("downstream-call"):
                delay = random.uniform(0.005, 0.05)  # noqa: S311 - non-crypto jitter
                time.sleep(delay)
            span.set_attribute("work.delay_ms", round(delay * 1000, 2))
            return {"status": "ok", "delay_ms": round(delay * 1000, 2)}, 200

    @app.get("/error")
    def error() -> tuple[dict, int]:
        with tracer.start_as_current_span("failing-op") as span:
            span.set_attribute("error", True)
            return {"status": "error", "detail": "simulated failure"}, 500

    return app


def main() -> None:  # pragma: no cover - manual run entrypoint
    exporter = os.environ.get("OTEL_EXPORTER", "none")
    port = int(os.environ.get("PORT", "8080"))
    # Binding to all interfaces is intentional for a containerized service.
    create_app(exporter=exporter).run(host="0.0.0.0", port=port)  # noqa: S104


if __name__ == "__main__":  # pragma: no cover
    main()
