"""OpenTelemetry setup and configuration"""

from contextlib import contextmanager
from typing import Dict, Any, Optional

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.trace import Status, StatusCode

from .config import get_settings

def setup_telemetry():
    """Initialize OpenTelemetry with all instrumentations"""
    settings = get_settings()
    
    if not settings.telemetry.enabled:
        return
    
    # Create resource with service information
    resource = Resource.create({
        "service.name": settings.telemetry.service_name,
        "service.version": settings.app_version,
        "deployment.environment": settings.environment,
    })
    
    # Setup tracing
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # Add OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.telemetry.otlp_endpoint,
        insecure=True
    )
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Setup metrics
    metric_reader = PeriodicExportingMetricReader(
        exporter=OTLPMetricExporter(
            endpoint=settings.telemetry.otlp_endpoint,
            insecure=True
        ),
        export_interval_millis=10000
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)
    
    # Auto-instrument libraries
    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()
    SQLAlchemyInstrumentor.instrument()
    RedisInstrumentor.instrument()

def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance"""
    return trace.get_tracer(name)

def get_meter(name: str) -> metrics.Meter:
    """Get a meter instance"""
    return metrics.get_meter(name)


class TelemetryManager:
    """Manager class for telemetry operations"""

    def __init__(self, service_name: Optional[str] = None):
        """Initialize telemetry manager

        Args:
            service_name: Name of the service for tracing
        """
        self.service_name = service_name or "mavn-bench"
        self.tracer = get_tracer(self.service_name)

    @contextmanager
    def traced_operation(self, operation_name: str, **attributes):
        """Create a traced operation context

        Args:
            operation_name: Name of the operation
            **attributes: Additional span attributes

        Returns:
            Trace context manager
        """
        with self.tracer.start_as_current_span(
            operation_name,
            attributes=attributes
        ) as span:
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
