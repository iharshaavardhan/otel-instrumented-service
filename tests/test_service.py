"""Tests for the instrumented service: endpoints, metrics, tracing, logging."""

import json
import logging

import pytest
from prometheus_client import generate_latest

from otel_service.app import create_app
from otel_service.logging_config import JsonFormatter
from otel_service.metrics import Metrics
from otel_service.tracing import configure_tracing, current_trace_ids


@pytest.fixture
def client():
    app = create_app(exporter="none")
    app.testing = True
    return app.test_client()


def test_healthz(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "alive"


def test_readyz(client):
    assert client.get("/readyz").status_code == 200


def test_work_ok(client):
    resp = client.get("/work")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert "delay_ms" in body


def test_error_endpoint_returns_500(client):
    assert client.get("/error").status_code == 500


def test_metrics_endpoint_exposes_red(client):
    # Generate some traffic first.
    client.get("/work")
    client.get("/error")
    metrics_text = client.get("/metrics").get_data(as_text=True)
    assert "http_requests_total" in metrics_text
    assert "http_request_duration_seconds" in metrics_text
    assert "http_requests_in_flight" in metrics_text
    # The error endpoint should have recorded a 500.
    assert 'code="500"' in metrics_text


def test_metrics_isolated_registry():
    m = Metrics()
    m.observe("GET", "/x", 200, 0.01)
    text = generate_latest(m.registry).decode()
    assert 'path="/x"' in text


def test_json_formatter_emits_valid_json():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="t", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello", args=(), exc_info=None,
    )
    record.status = 200
    record.duration_ms = 12.5
    parsed = json.loads(formatter.format(record))
    assert parsed["message"] == "hello"
    assert parsed["level"] == "info"
    assert parsed["status"] == 200
    assert parsed["duration_ms"] == 12.5


def test_tracing_produces_ids_within_span():
    tracer = configure_tracing(exporter="none")
    with tracer.start_as_current_span("t"):
        trace_id, span_id = current_trace_ids()
        assert trace_id is not None and len(trace_id) == 32
        assert span_id is not None and len(span_id) == 16


def test_no_active_span_returns_none():
    # Outside any span, ids should be None.
    trace_id, span_id = current_trace_ids()
    assert trace_id is None and span_id is None
