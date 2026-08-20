from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from contextlib import contextmanager

# Initialize global tracer provider for local/dev environment
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("aegis.credit_risk_agent")

@contextmanager
def trace_span(span_name: str, attributes: dict = None):
    """
    Context manager to wrap operations in OpenTelemetry spans.
    """
    with tracer.start_as_current_span(span_name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        yield span