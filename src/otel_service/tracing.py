"""OpenTelemetry tracing setup.

`configure_tracing` sets up a TracerProvider with a selectable exporter:
  * "none"    — no exporter (default; zero external dependency, good for tests)
  * "console" — prints spans to stdout (local debugging)
  * "otlp"    — exports to an OTLP collector endpoint (real deployments)

Kept import-light so the service runs even if the OTLP exporter extra is not
installed.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)


def configure_tracing(
    service_name: str = "otel-instrumented-service",
    exporter: str = "none",
    otlp_endpoint: str | None = None,
) -> trace.Tracer:
    """Configure a global TracerProvider and return a tracer."""
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    exporter = exporter.lower()
    if exporter == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    elif exporter == "otlp":
        # Imported lazily: the OTLP exporter is an optional dependency.
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # noqa: PLC0415
            OTLPSpanExporter,
        )

        endpoint = otlp_endpoint or "http://localhost:4318/v1/traces"
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    # "none" -> provider with no exporter (spans are created but not exported).

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)


def current_trace_ids() -> tuple[str | None, str | None]:
    """Return (trace_id, span_id) hex strings for the active span, if any."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx or not ctx.is_valid:
        return None, None
    return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")
