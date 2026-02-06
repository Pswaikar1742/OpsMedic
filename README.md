# OpsMedic

OpsMedic is an autonomous Site Reliability Engineering (SRE) agent designed to proactively prevent service outages by detecting and remediating infrastructure degradation before it leads to a crash. It operates on a "Perceive-Reason-Act" loop, ensuring high availability and reliability of services.

---

## 🌟 Key Features

### 1. Perceive (Observe & Detect Degradation)
- **Mechanism:** Utilizes OpenTelemetry for comprehensive application health monitoring, including metrics, traces, and logs.
- **Trigger:** Detects Service Level Objective (SLO) breaches or anomalies, such as:
  - Memory utilization > 90% for 120 seconds.
  - P99 latency > 1.5 seconds for 60 seconds.
- **Output:** Provides rich, correlated observability data for further analysis.

### 2. Reason (AI-Powered Diagnosis)
- **Mechanism:** Leverages a Large Language Model (LLM) to act as a virtual Senior SRE.
- **Input:** Structured payload containing detailed OpenTelemetry context, including metric trends, trace IDs, correlated log snippets, and SLO details.
- **Output:** A structured JSON response with:
  - Root cause analysis.
  - Recommended remediation actions (e.g., RESTART, SCALE_OUT, ROLLBACK).

### 3. Act (Intelligent Remediation)
- **Mechanism:** Executes recommended actions automatically.
- **Actions:**
  - **RESTART:** Restarts affected Docker containers.
  - **SCALE_OUT:** Scales out services to handle increased load (future feature).
  - **ROLLBACK:** Reverts to a stable version (future feature).
- **Target:** Docker containers (current MVP) with plans to integrate Kubernetes API in future phases.

### 4. Dashboard
- **Streamlit-based Dashboard:**
  - Visualizes incidents and container status in real-time.
  - Displays live updates of the incident lifecycle.

---

## 🏗️ Project Structure

```
OpsMedic/
├── buggy_app_v2/          # Instrumented application with OpenTelemetry
├── opsmedic_agent/        # FastAPI app for receiving webhooks and orchestrating LLM diagnosis
├── opsmedic_dashboard/    # Streamlit dashboard for visualization
├── docs/                  # Documentation files (not pushed to GitHub)
├── docker-compose.yaml    # Docker Compose configuration for the project
└── otel-collector-config.yaml # OpenTelemetry Collector configuration
```

---

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose installed.
- Python 3.10+ installed.
- An LLM API key (choose at least one):
  - **Google Gemini:** Get your API key from [Google AI Studio](https://aistudio.google.com/apikey).
  - **FastRouter:** Get your API key from [FastRouter](https://www.fastrouter.ai/).
  - **Llama (Self-hosted):** A running Llama endpoint and API key.

### API Key Configuration

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your API keys:**
   ```bash
   # .env file
   ACTIVE_LLM_PROVIDER=gemini  # or 'fastrouter' or 'llama'
   GEMINI_API_KEY=your_gemini_key_here
   FASTRTR_API_KEY=your_fastrouter_key_here
   LLAMA_API_KEY=your_llama_key_here
   LLAMA_ENDPOINT=http://your-llama-endpoint:port
   ```

3. **DO NOT commit `.env` to version control!** It's already in `.gitignore`.

### Setup Instructions

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/Pswaikar1742/OpsMedic.git
   cd OpsMedic
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your LLM API keys (see API Key Configuration above)
   ```

3. **Build and Start the Services:**
   ```bash
   docker-compose up --build
   ```

4. **Access the Dashboard:**
   Open your browser and navigate to:
   ```
   http://localhost:8501
   ```

5. **Run Integration Tests:**
   To ensure everything is working as expected, run:
   ```bash
   cd opsmedic_project
   pytest opsmedic_agent/tests/ -v
   ```

---

## 📚 Documentation

All project documentation, including progress reports, demo scripts, and integration testing instructions, can be found in the `docs/` folder. Note that this folder is excluded from the GitHub repository.

---

## 🤝 Contributing

We welcome contributions to improve OpsMedic! To contribute:

1. Fork the repository.
2. Create a new branch for your feature:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m 'Add some feature'
   ```
4. Push to the branch:
   ```bash
   git push origin feature-name
   ```
5. Open a pull request.

---

## 📜 License

This project is licensed under the MIT License. See the LICENSE file for details.

---

## 🛠️ Future Enhancements

- **Kubernetes Integration:** Extend remediation capabilities to Kubernetes clusters.
- **Advanced AI Diagnosis:** Incorporate more advanced LLMs for better root cause analysis.
- **Additional Remediation Actions:** Add support for scaling out and rolling back services.
- **Enhanced Dashboard Features:**
  - Historical data visualization.
  - Customizable SLO thresholds.
  - User authentication and role-based access control.
---

Thank you for using OpsMedic! Together, let's make infrastructure more reliable and resilient.
