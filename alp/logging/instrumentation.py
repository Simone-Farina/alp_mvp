from __future__ import annotations

import os

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

try:
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
except ImportError:
    OTLPSpanExporter = None  # optional

OTEL_ENABLED = os.getenv("ALP_OTEL_ENABLED", "1") not in ("0", "false", "False")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")  # e.g. http://localhost:4318/v1/traces
SERVICE_NAME = os.getenv("ALP_SERVICE_NAME", "alp-app")

_tracer = None


def init_tracing():
    global _tracer
    if not OTEL_ENABLED:
        return None

    resource = Resource.create({
        "service.name": SERVICE_NAME,
        "service.version": os.getenv("ALP_VERSION", "0.1.0")
    })
    provider = TracerProvider(resource=resource)

    # Always console exporter for dev
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # Optional OTLP (to collector)
    if OTLP_ENDPOINT and OTLPSpanExporter:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True))
        )

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(SERVICE_NAME)
    return _tracer


def get_tracer():
    return _tracer or trace.get_tracer(SERVICE_NAME)


# Decorator helper
def traced(name: str | None = None):
    def deco(fn):
        span_name = name or fn.__qualname__

        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("code.function", fn.__name__)
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.status.Status(trace.status.StatusCode.ERROR, str(e)))
                    raise

        return wrapper

    return deco
