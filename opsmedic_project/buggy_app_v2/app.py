from flask import Flask, jsonify
from opentelemetry import trace
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
import psutil
import os

# Initialize Flask app
app = Flask(__name__)

# OpenTelemetry setup
trace.set_tracer_provider(TracerProvider())
otlp_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Instrument Flask with OpenTelemetry
FlaskInstrumentor().instrument_app(app)

# Global variable to simulate memory leak
memory_leak_list = []

# OpenTelemetry Metrics setup
meter_provider = MeterProvider(
    metric_readers=[
        PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint="http://otel-collector:4317", insecure=True)
        )
    ]
)
metrics = meter_provider.get_meter(__name__)

# Create a custom metric for memory usage
memory_usage_metric = metrics.create_observable_gauge(
    name="container_memory_usage_bytes",
    description="Memory usage of the application container",
    unit="bytes",
    callbacks=[
        lambda: [
            (
                {
                    "container_id": os.getenv("CONTAINER_ID", "unknown"),
                    "container_name": os.getenv("CONTAINER_NAME", "buggy-app-v2"),
                    "container_image": os.getenv("CONTAINER_IMAGE", "unknown")
                },
                psutil.Process(os.getpid()).memory_info().rss
            )
        ]
    ]
)

# Set the meter provider
metrics.set_meter_provider(meter_provider)

@app.route("/")
def root():
    return "Hello from Buggy App V2!"

@app.route("/health")
def health():
    return "OK"

@app.route("/memory_leak")
def memory_leak():
    global memory_leak_list
    memory_leak_list.append("X" * 1024 * 1024)  # Add 1MB to the list
    return jsonify({"message": "Memory consumed. Current size: {} MB".format(len(memory_leak_list))})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)