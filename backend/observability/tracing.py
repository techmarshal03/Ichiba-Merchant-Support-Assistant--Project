"""
OpenTelemetry tracing setup for AKS + Azure Monitor integration.
"""
from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from backend.config import settings

log = logging.getLogger(__name__)


def setup_tracing() -> None:
    """Configure OTLP tracing to Azure Monitor / Jaeger collector."""
    resource = Resource.create(
        {
            "service.name": "ichiba-merchant-support",
            "service.version": settings.app_version,
            "deployment.environment": settings.environment,
        }
    )

    provider = TracerProvider(resource=resource)

    if settings.otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        log.info("OTLP tracing → %s", settings.otlp_endpoint)
    else:
        log.warning("OTLP_ENDPOINT not set — tracing disabled")

    trace.set_tracer_provider(provider)


def get_tracer() -> trace.Tracer:
    return trace.get_tracer("ichiba.merchant.support")
