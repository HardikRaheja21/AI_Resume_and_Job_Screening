from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

from .config import settings

try:
    from opentelemetry import context as otel_context, trace
    from opentelemetry.propagate import extract, inject
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    _OTEL_AVAILABLE = True
except Exception:  # pragma: no cover
    trace = None  # type: ignore
    otel_context = None  # type: ignore
    extract = None  # type: ignore
    inject = None  # type: ignore
    _OTEL_AVAILABLE = False


_CONFIGURED = False


def configure_tracing() -> None:
    global _CONFIGURED
    if _CONFIGURED or not settings.OTEL_ENABLE or not _OTEL_AVAILABLE:
        return
    resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
    provider = TracerProvider(resource=resource)
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT))
        )
    trace.set_tracer_provider(provider)
    _CONFIGURED = True


def tracer(name: str = "resume_parser") -> Any:
    configure_tracing()
    if _OTEL_AVAILABLE:
        return trace.get_tracer(name)
    return None


@contextmanager
def start_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    trace_context: Optional[Dict[str, str]] = None,
) -> Iterator[Any]:
    current = tracer()
    if current is None:
        yield None
        return
    parent_context = extract_trace_context(trace_context) if trace_context else None
    token = None
    try:
        if parent_context is not None and _OTEL_AVAILABLE:
            token = otel_context.attach(parent_context)
        with current.start_as_current_span(name) as span:
            for key, value in (attributes or {}).items():
                try:
                    span.set_attribute(key, value)
                except Exception:
                    pass
            yield span
    finally:
        if token is not None and _OTEL_AVAILABLE:
            otel_context.detach(token)


def inject_trace_context(carrier: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    output = carrier or {}
    if _OTEL_AVAILABLE:
        inject(output)
    return output


def extract_trace_context(carrier: Optional[Dict[str, str]]) -> Any:
    if _OTEL_AVAILABLE:
        return extract(carrier or {})
    return None
