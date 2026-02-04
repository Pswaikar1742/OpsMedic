# OpsMedic: Instructions for Development

## Project Overview

**Project Name:** OpsMedic (Autonomous SRE Agent)

**Vision:** To build a proactive, autonomous SRE agent that prevents service outages by detecting and remediating infrastructure degradation before it leads to a crash. It embodies a true "Perceive-Reason-Act" loop.

### Core Workflow (Perceive-Reason-Act Loop):

1. **Perceive (Observe & Detect Degradation):**
   - **Mechanism:** OpenTelemetry (Metrics, Traces, Logs) for comprehensive application health sensing.
   - **Trigger:** Detection of Service Level Objective (SLO) breaches or anomalies (e.g., memory > 90% for 120s, P99 latency > 1.5s for 60s).
   - **Output:** Rich, correlated observability data.

2. **Reason (AI-Powered Diagnosis):**
   - **Mechanism:** Large Language Model (LLM) acting as a Senior SRE.
   - **Input:** Structured payload containing detailed OTel context (metric trends, specific trace IDs, correlated log snippets, SLO details).
   - **Output:** Structured JSON response from LLM, e.g., `{ "root_cause": "Memory Leak in X function", "recommended_action": "RESTART" }`.

3. **Act (Intelligent Remediation):**
   - **Mechanism:** Automated execution of recommended actions.
   - **Actions:** Primarily RESTART for our MVP. Future: SCALE_OUT, ROLLBACK, IGNORE.
   - **Target:** Docker containers (via Docker SDK). Future: Kubernetes API.

---

## Technical Stack

- **Language:** Python 3.10+
- **Observability:** OpenTelemetry (Python SDK for instrumentation, OTel Collector for collection/processing/export)
- **AI/Agent Framework:** LangGraph (for complex agentic workflows, though for MVP we might keep it simpler).
- **LLM Integration:** Generalized abstraction layer to support various LLMs.
  - Primary Options: Google Gemini 1.5 Flash (via google-generativeai) and a custom Llama endpoint (via requests for neysa.io or FastRouter credits).
- **Infrastructure Control:** Docker SDK for Python
- **Backend/API:** FastAPI (for opsmedic-agent's webhook receiver and potentially a dashboard data endpoint).
- **Frontend/Dashboard:** Streamlit
- **Orchestration:** Docker Compose (for local development setup).
- **Environment:** Local Docker Desktop.

---

## Core Architectural Components

1. **Instrumented Application (buggy-app-v2):**
   - Python app instrumented with OTel SDK.

2. **OpenTelemetry Collector (otel-collector):**
   - Docker container, configured via `otel-collector-config.yaml`.
   - Receives OTLP, processes, detects SLOs, exports webhooks.

3. **OpsMedic Agent (opsmedic-agent):**
   - FastAPI app.
   - Receives OTel webhooks, orchestrates LLM diagnosis, and executes remediation.

4. **AI Core (LLM Abstraction):**
   - Internal module for LLM selection and prompt formatting.

5. **Remediation Executor:**
   - Internal module for executing Docker commands.

6. **OpsMedic Dashboard (opsmedic-dashboard):**
   - Streamlit app for visualization and reporting.

7. **External LLM Service:**
   - Abstracted endpoint for Gemini, Llama, FastRouter, etc.

---

## Key Data Contract

**Incident Payload JSON (from OTel Collector webhook to OpsMedic Agent):**

```json
{
  "incident_id": "a_unique_uuid",
  "timestamp": "iso_8601_timestamp_of_alert",
  "breached_slo": "memory_utilization_90_percent_for_120s",
  "container_info": {
    "id": "short_container_id",
    "name": "container_name",
    "image": "docker_image_name"
  },
  "observability_context": {
    "metrics_snapshot": { /* JSON of relevant metric values/trends */ },
    "trace_ids": ["trace_id_1", "trace_id_2"], /* list of slow trace IDs */
    "correlated_logs": "Recent log snippets related to the incident."
  }
}
```

---

## Development Phase & Immediate Focus

**Current Phase:** Phase 1 - Observability Backbone & Agent Skeleton

**Immediate Tasks:**

1. Finalize hackathon submission docs (PPT, Figma, README).
2. Set up `docker-compose`.
3. Create `otel-collector-config.yaml`.
4. Add basic OTel instrumentation in `buggy-app-v2`.
5. Develop FastAPI webhook receiver in `opsmedic-agent`.
6. Create LLM client skeletons.

**Hackathon Deadline:** February 7th, 2026.

---

## Development Guidelines

1. **Modular Code:**
   - Write functions and classes that are self-contained and reusable.

2. **Clear Instructions:**
   - Provide step-by-step guidance for integration and setup.

3. **Error Handling & Documentation:**
   - Include basic error handling and comments in all code.

4. **Time Efficiency:**
   - Suggest the most direct and impactful implementation paths.

5. **Holistic Context:**
   - Understand that the developer is responsible for all aspects (frontend, backend, AI, infra).

6. **Security Best Practices:**
   - Use `.env` files for API key management.

---

## Next Steps

1. **Set up Docker Compose:**
   - Create a `docker-compose.yml` file to orchestrate the services.

2. **Configure OpenTelemetry Collector:**
   - Create `otel-collector-config.yaml` for OTLP collection and processing.

3. **Instrument `buggy-app-v2`:**
   - Add OpenTelemetry Python SDK instrumentation.

4. **Develop FastAPI Webhook Receiver:**
   - Create a FastAPI app to receive webhooks from the OTel Collector.

5. **LLM Client Skeleton:**
   - Develop a generalized abstraction layer for LLM integration.

6. **Prepare Hackathon Submission Docs:**
   - Finalize PPT, Figma designs, and README.

---

This document will be updated as the project progresses.