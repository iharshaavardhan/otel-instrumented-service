# syntax=docker/dockerfile:1
FROM python:3.12-slim

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin appuser
WORKDIR /app

COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir . gunicorn

ENV PORT=8080 \
    OTEL_EXPORTER=none \
    PYTHONUNBUFFERED=1

USER appuser
EXPOSE 8080

# gunicorn serves the Flask app via the factory. 2 workers, gthread for I/O.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", \
     "otel_service.app:create_app()"]
