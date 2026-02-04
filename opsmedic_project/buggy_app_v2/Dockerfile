# Use Python 3.10 base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py app.py

# Set environment variables for OpenTelemetry
ENV OTEL_SERVICE_NAME=buggy-app-v2
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]