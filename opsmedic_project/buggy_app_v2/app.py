from flask import Flask, jsonify, request
import logging
import sys
from opentelemetry import trace, metrics, logs
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.logs import LoggerProvider
from opentelemetry.sdk.logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc.log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
import psutil
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# OpenTelemetry Trace setup
trace_provider = TracerProvider()
otlp_trace_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
    insecure=True
)
trace_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))
trace.set_tracer_provider(trace_provider)

# OpenTelemetry Metrics setup
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
        insecure=True
    )
)
meter_provider = MeterProvider(metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

# OpenTelemetry Logs setup
log_provider = LoggerProvider()
otlp_log_exporter = OTLPLogExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
    insecure=True
)
log_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_log_exporter))
logs.set_logger_provider(log_provider)
LoggingInstrumentor().instrument()

# Instrument Flask
FlaskInstrumentor().instrument_app(app)
RequestsInstrumentor().instrument()

# Create custom metrics
request_counter = meter.create_counter(
    name="app_requests_total",
    description="Total number of requests",
    unit="1"
)

memory_gauge = meter.create_observable_gauge(
    name="container_memory_usage_bytes",
    description="Memory usage of the application container",
    unit="bytes",
    callbacks=[lambda options: [(
        {
            "container_id": os.getenv("CONTAINER_ID", "unknown"),
            "container_name": os.getenv("CONTAINER_NAME", "buggy-app-v2"),
        },
        psutil.Process(os.getpid()).memory_info().rss
    )]]
)

# Global variable to simulate memory leak
memory_leak_list = []
tracer = trace.get_tracer(__name__)

@app.before_request
def before_request():
    """Log incoming requests."""
    logger.info(f"Incoming request: {request.method} {request.path}")

@app.route("/")
def root():
    request_counter.add(1, {"endpoint": "/"})
    logger.info("Root endpoint accessed")
    return "Hello from Buggy App V2!"

@app.route("/health")
def health():
    request_counter.add(1, {"endpoint": "/health"})
    memory_mb = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    logger.info(f"Health check - Memory: {memory_mb:.2f}MB")
    return jsonify({"status": "ok", "memory_mb": memory_mb})

@app.route("/memory_leak")
def memory_leak():
    """Endpoint to simulate memory leak."""
    global memory_leak_list
    with tracer.start_as_current_span("memory_leak_operation") as span:
        memory_leak_list.append("X" * 1024 * 1024)  # Add 1MB
        memory_mb = len(memory_leak_list)
        logger.warning(f"Memory leak endpoint called. Current leak size: {memory_mb}MB")
        span.set_attribute("leak_size_mb", memory_mb)
        request_counter.add(1, {"endpoint": "/memory_leak"})
        return jsonify({"message": f"Memory consumed. Current size: {memory_mb}MB"})

@app.route("/stress")
def stress():
    """Endpoint to create CPU/IO stress."""
    with tracer.start_as_current_span("stress_operation"):
        # Simulate CPU work
        for i in range(1000000):
            _ = i ** 2
        logger.info("Stress endpoint: completed CPU work")
        request_counter.add(1, {"endpoint": "/stress"})
        return jsonify({"message": "Stress test completed"})

@app.errorhandler(Exception)
def handle_error(error):
    """Handle exceptions and log them."""
    logger.error(f"Error: {str(error)}", exc_info=True)
    return jsonify({"error": str(error)}), 500

if __name__ == "__main__":
    logger.info("Starting Buggy App V2")
    app.run(host="0.0.0.0", port=8000, debug=False)