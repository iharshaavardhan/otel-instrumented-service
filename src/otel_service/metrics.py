"""Prometheus RED metrics (Rate, Errors, Duration).

Exposes:
  * http_requests_total{method,path,code}   — Rate + Errors (by code)
  * http_request_duration_seconds{method,path} — Duration (histogram)
  * http_requests_in_flight                 — concurrency gauge

A dedicated CollectorRegistry is used so tests can assert on metrics in
isolation without leaking global state.
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram


class Metrics:
    """RED metrics bound to a specific registry."""

    def __init__(self, registry: CollectorRegistry | None = None):
        self.registry = registry or CollectorRegistry()

        self.requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests.",
            ["method", "path", "code"],
            registry=self.registry,
        )
        self.request_duration = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds.",
            ["method", "path"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
            registry=self.registry,
        )
        self.in_flight = Gauge(
            "http_requests_in_flight",
            "In-flight HTTP requests.",
            registry=self.registry,
        )

    def observe(self, method: str, path: str, code: int, duration_seconds: float) -> None:
        """Record one completed request."""
        self.requests_total.labels(method=method, path=path, code=str(code)).inc()
        self.request_duration.labels(method=method, path=path).observe(duration_seconds)
