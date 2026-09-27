"""Structured JSON logging.

Emits one JSON object per log line so logs are machine-parseable by downstream
aggregators. When a trace is active, the trace/span ids are attached so logs can
be correlated with traces.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON with optional trace correlation."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach structured extras.
        for key in ("method", "path", "status", "duration_ms", "trace_id", "span_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def get_logger(name: str = "otel_service", level: int = logging.INFO) -> logging.Logger:
    """Return a logger that writes structured JSON to stdout (idempotent)."""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
