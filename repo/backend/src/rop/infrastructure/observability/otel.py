from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

_OTEL_CONFIGURED = False
logger = logging.getLogger(__name__)


def configure_otel(app: FastAPI) -> None:
    global _OTEL_CONFIGURED
    if _OTEL_CONFIGURED:
        return

    service_name = os.getenv("OTEL_SERVICE_NAME", "rop-backend")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    if endpoint:
        try:
            exporter = OTLPSpanExporter(
                endpoint=endpoint,
                insecure=endpoint.startswith("http://"),
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception:
            logger.exception("otel_exporter_setup_failed")

    trace.set_tracer_provider(provider)
    set_global_textmap(TraceContextTextMapPropagator())
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    _OTEL_CONFIGURED = True
