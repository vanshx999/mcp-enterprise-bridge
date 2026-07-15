from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from core.config import settings
from core.logging import logger


def init_otel() -> None:
    if not settings.otel_enabled:
        logger.info("OpenTelemetry disabled — no endpoint configured")
        return

    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "service.version": "0.1.0",
        "deployment.environment": settings.environment,
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=f"{settings.otel_endpoint.rstrip('/')}/v1/traces",
        timeout=5,
    )
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    logger.info(f"OpenTelemetry initialized — exporting to {settings.otel_endpoint}")


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(settings.otel_service_name)
