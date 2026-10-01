import logging
from unittest.mock import patch

import pytest
from opentelemetry import baggage, trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.instrumentation.logging.handler import LoggingHandler
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF
from opentelemetry.trace import StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


def test_resource_create_adds_sdk_attributes_and_preserves_user_attributes():
    resource = Resource.create(
        {
            "deployment.environment": "test",
            "service.name": "compatibility-suite",
        }
    )

    assert resource.attributes["deployment.environment"] == "test"
    assert resource.attributes["service.name"] == "compatibility-suite"
    assert resource.attributes["service.instance.id"]
    assert resource.attributes["telemetry.sdk.language"] == "python"
    assert resource.attributes["telemetry.sdk.name"] == "opentelemetry"
    assert resource.attributes["telemetry.sdk.version"]


def test_resource_create_honors_standard_environment_attributes(monkeypatch):
    monkeypatch.setenv("OTEL_SERVICE_NAME", "environment-service")
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "deployment.environment=production,service.version=2.1")

    resource = Resource.create({"service.name": "explicit-service"})

    assert resource.attributes["service.name"] == "explicit-service"
    assert resource.attributes["deployment.environment"] == "production"
    assert resource.attributes["service.version"] == "2.1"


def test_tracing_exports_parent_child_spans_with_events_and_attributes():
    exporter = InMemorySpanExporter()
    provider = TracerProvider(
        resource=Resource.create({"service.name": "compatibility-suite"}),
        shutdown_on_exit=False,
    )
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("compatibility-tests", "1.0")

    with tracer.start_as_current_span("parent") as parent:
        parent.set_attribute("request.id", "request-123")
        parent.add_event("request.received", {"payload.size": 42})
        with tracer.start_as_current_span("child") as child:
            child.set_attribute("component", "dependency")

    spans = {span.name: span for span in exporter.get_finished_spans()}
    parent_span = spans["parent"]
    child_span = spans["child"]

    assert child_span.context.trace_id == parent_span.context.trace_id
    assert child_span.parent.span_id == parent_span.context.span_id
    assert parent_span.attributes is not None
    assert parent_span.attributes["request.id"] == "request-123"
    assert parent_span.events[0].name == "request.received"
    assert parent_span.events[0].attributes is not None
    assert parent_span.events[0].attributes["payload.size"] == 42
    assert parent_span.resource.attributes["service.name"] == "compatibility-suite"
    assert parent_span.instrumentation_scope.name == "compatibility-tests"
    provider.shutdown()


def test_always_off_sampler_creates_non_recording_span_and_exports_nothing():
    exporter = InMemorySpanExporter()
    provider = TracerProvider(sampler=ALWAYS_OFF, shutdown_on_exit=False)
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    with provider.get_tracer("compatibility-tests").start_as_current_span("dropped") as span:
        assert not span.is_recording()
        assert not span.get_span_context().trace_flags.sampled

    assert not exporter.get_finished_spans()
    provider.shutdown()


def test_record_exception_sets_error_status_and_exception_event():
    exporter = InMemorySpanExporter()
    provider = TracerProvider(shutdown_on_exit=False)
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("compatibility-tests")

    with pytest.raises(ValueError, match="bad input"):
        with tracer.start_as_current_span("failing-operation"):
            raise ValueError("bad input")

    span = exporter.get_finished_spans()[0]
    assert span.status.status_code is StatusCode.ERROR
    assert span.events[0].name == "exception"
    assert span.events[0].attributes is not None
    assert span.events[0].attributes["exception.type"] == "ValueError"
    assert span.events[0].attributes["exception.message"] == "bad input"
    provider.shutdown()


def test_tracer_provider_force_flush_reaches_span_processor():
    exporter = InMemorySpanExporter()
    provider = TracerProvider(shutdown_on_exit=False)
    processor = SimpleSpanProcessor(exporter)
    provider.add_span_processor(processor)

    with provider.get_tracer("compatibility-tests").start_as_current_span("flush-me"):
        pass

    with patch.object(processor, "force_flush", wraps=processor.force_flush) as force_flush:
        assert provider.force_flush(timeout_millis=1_000)

    force_flush.assert_called_once()
    assert [span.name for span in exporter.get_finished_spans()] == ["flush-me"]
    provider.shutdown()


def test_metrics_collect_counter_and_histogram_measurements():
    reader = InMemoryMetricReader()
    provider = MeterProvider(
        metric_readers=[reader],
        resource=Resource.create({"service.name": "compatibility-suite"}),
        shutdown_on_exit=False,
    )
    meter = provider.get_meter("compatibility-tests", "1.0")

    meter.create_counter("requests").add(3, {"route": "/orders"})
    meter.create_histogram("request.duration", unit="ms").record(12.5, {"route": "/orders"})

    metrics_data = reader.get_metrics_data()
    resource_metrics = metrics_data.resource_metrics[0]
    metrics = {
        metric.name: metric for scope_metrics in resource_metrics.scope_metrics for metric in scope_metrics.metrics
    }

    counter_point = metrics["requests"].data.data_points[0]
    histogram_point = metrics["request.duration"].data.data_points[0]
    assert counter_point.value == 3
    assert counter_point.attributes == {"route": "/orders"}
    assert histogram_point.count == 1
    assert histogram_point.sum == 12.5
    assert histogram_point.min == 12.5
    assert histogram_point.max == 12.5
    assert histogram_point.attributes == {"route": "/orders"}
    assert resource_metrics.resource.attributes["service.name"] == "compatibility-suite"
    provider.shutdown()


def test_metrics_collect_up_down_counter_measurements():
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader], shutdown_on_exit=False)
    counter = provider.get_meter("compatibility-tests").create_up_down_counter("active.requests")

    counter.add(3, {"queue": "primary"})
    counter.add(-1, {"queue": "primary"})

    metric = reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics[0]
    point = metric.data.data_points[0]
    assert point.value == 2
    assert point.attributes == {"queue": "primary"}
    provider.shutdown()


def test_logging_handler_exports_formatted_body_attributes_and_scope():
    exporter = InMemoryLogRecordExporter()
    provider = LoggerProvider(
        resource=Resource.create({"service.name": "compatibility-suite"}),
        shutdown_on_exit=False,
    )
    provider.add_log_record_processor(SimpleLogRecordProcessor(exporter))
    handler = LoggingHandler(logger_provider=provider)
    logger = logging.getLogger("compatibility-tests")
    original_handlers = logger.handlers[:]
    original_level = logger.level
    original_propagate = logger.propagate

    try:
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.info("processed %s items", 5, extra={"request_id": "request-123"})

        exported = exporter.get_finished_logs()
        assert len(exported) == 1
        record = exported[0]
        assert record.log_record.body == "processed 5 items"
        assert record.log_record.attributes is not None
        assert record.log_record.attributes["request_id"] == "request-123"
        assert record.instrumentation_scope.name == "compatibility-tests"
        assert record.resource.attributes["service.name"] == "compatibility-suite"
    finally:
        logger.handlers = original_handlers
        logger.setLevel(original_level)
        logger.propagate = original_propagate
        provider.shutdown()


def test_log_record_carries_active_trace_context():
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider(shutdown_on_exit=False)
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    log_exporter = InMemoryLogRecordExporter()
    logger_provider = LoggerProvider(shutdown_on_exit=False)
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
    logger = logging.getLogger("trace-correlated-logger")
    handler = LoggingHandler(logger_provider=logger_provider)
    original_handlers = logger.handlers[:]
    original_propagate = logger.propagate
    logger.handlers = [handler]
    logger.propagate = False

    try:
        with tracer_provider.get_tracer("compatibility-tests").start_as_current_span("operation") as span:
            logger.warning("correlated")

        record = log_exporter.get_finished_logs()[0].log_record
        assert record.trace_id == span.get_span_context().trace_id
        assert record.span_id == span.get_span_context().span_id
        assert record.trace_flags == span.get_span_context().trace_flags
    finally:
        logger.handlers = original_handlers
        logger.propagate = original_propagate
        logger_provider.shutdown()
        tracer_provider.shutdown()


def test_w3c_trace_context_and_baggage_round_trip():
    provider = TracerProvider(shutdown_on_exit=False)
    tracer = provider.get_tracer("compatibility-tests")
    propagator = CompositePropagator(
        [
            TraceContextTextMapPropagator(),
            W3CBaggagePropagator(),
        ]
    )

    with tracer.start_as_current_span("producer") as span:
        context = baggage.set_baggage("tenant.id", "tenant-123")
        carrier = {}
        propagator.inject(carrier, context=context)

    extracted_context = propagator.extract(carrier)
    extracted_span_context = trace.get_current_span(extracted_context).get_span_context()

    assert carrier["traceparent"].startswith("00-")
    assert carrier["baggage"] == "tenant.id=tenant-123"
    assert extracted_span_context.trace_id == span.get_span_context().trace_id
    assert extracted_span_context.span_id == span.get_span_context().span_id
    assert baggage.get_baggage("tenant.id", context=extracted_context) == "tenant-123"
    provider.shutdown()


def test_invalid_traceparent_is_ignored():
    extracted_context = TraceContextTextMapPropagator().extract({"traceparent": "invalid"})

    assert not trace.get_current_span(extracted_context).get_span_context().is_valid
