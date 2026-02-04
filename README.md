# OpsMedic

OpsMedic is an autonomous SRE agent designed to prevent service outages by detecting and remediating infrastructure degradation before it leads to a crash. It embodies a true "Perceive-Reason-Act" loop.

## Features

- **Perceive:** Observes and detects degradation using OpenTelemetry for metrics, traces, and logs.
- **Reason:** Diagnoses issues using an AI-powered Large Language Model (LLM) to identify root causes and recommend actions.
- **Act:** Executes intelligent remediation actions such as restarting containers, scaling out, or rolling back.
- **Dashboard:** A Streamlit-based dashboard to visualize incidents and container status in real-time.

## Project Structure

```
OpsMedic/
├── buggy_app_v2/          # Instrumented application with OpenTelemetry
├── opsmedic_agent/        # FastAPI app for receiving webhooks and orchestrating LLM diagnosis
├── opsmedic_dashboard/    # Streamlit dashboard for visualization
├── docs/                  # Documentation files (not pushed to GitHub)
├── docker-compose.yaml    # Docker Compose configuration for the project
└── otel-collector-config.yaml # OpenTelemetry Collector configuration
```

## Getting Started

### Prerequisites

- Docker and Docker Compose installed
- Python 3.10+

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd OpsMedic
   ```

2. Build and start the services:
   ```bash
   docker-compose up --build
   ```

3. Access the Streamlit dashboard at `http://localhost:8501`.

### Testing

Run the integration tests:
```bash
pytest opsmedic_agent/tests/
```

## Contributing

1. Fork the repository.
2. Create a new branch for your feature (`git checkout -b feature-name`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature-name`).
5. Open a pull request.

## License

This project is licensed under the MIT License.
