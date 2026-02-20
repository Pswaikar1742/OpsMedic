# OpsMedic — Codebase Context & State Document

> **Purpose:** A comprehensive reference for an AI architect to understand the current state, architecture, data flow, capabilities, and gaps of the OpsMedic autonomous SRE agent.

---

## 1. Project Structure

```
OpsMedic/
├── .env.example                             # LLM API key template
├── .gitignore
├── README.md                                # Project overview & setup guide
├── CODEBASE_CONTEXT.md                      # ← This document
├── docker-compose.yaml                      # Orchestrates all 4 services
│
└── opsmedic_project/
    ├── README.md                            # Inner project readme
    ├── requirements.txt                     # (empty — deps are per-service)
    ├── otel-collector-config.yaml           # OTel Collector pipeline config
    │
    ├── buggy_app_v2/                        # Target app (Flask + OTel)
    │   ├── Dockerfile
    │   ├── app.py                           # Flask app with /memory_leak, /stress endpoints
    │   ├── requirements.txt                 # flask, gunicorn, opentelemetry-*
    │   └── __init__.py
    │
    ├── opsmedic_agent/                      # Core SRE agent (FastAPI)
    │   ├── Dockerfile
    │   ├── main.py                          # Webhook receiver, orchestration, incident DB
    │   ├── requirements.txt                 # fastapi, docker, google-generativeai, etc.
    │   ├── __init__.py
    │   ├── ai_core/
    │   │   ├── llm_client.py               # LLM abstraction (Gemini, Llama, FastRouter)
    │   │   └── __init__.py
    │   ├── remediation_executor/
    │   │   ├── docker_actions.py            # Docker SDK restart logic
    │   │   └── __init__.py
    │   └── tests/
    │       └── test_llm_client.py           # Unit tests for LLM diagnosis
    │
    └── opsmedic_dashboard/                  # Real-time dashboard (Streamlit)
        ├── Dockerfile
        ├── app.py                           # Dashboard UI with auto-refresh
        ├── requirements.txt                 # streamlit, requests, pandas
        └── __init__.py
```

---

## 2. Component Breakdown

### 2.1 FastAPI Backend (`opsmedic_agent/main.py`)

The central orchestration service. It implements the **Perceive → Reason → Act** loop.

| Route | Method | Purpose |
|---|---|---|
| `/webhook` | POST | Receives incident alert payloads, validates via Pydantic, calls LLM for diagnosis, executes Docker remediation if action is `RESTART`, stores incident record in-memory. |
| `/incidents` | GET | Returns the last N incident records (default 100) from the in-memory DB. |
| `/health` | GET | Health check — returns `{"status": "healthy", "incidents_stored": <count>}`. |
| `/` | GET | Service info and available endpoints. |

- **Authentication:** Optional Bearer token via `AGENT_API_KEY` env var.
- **Storage:** In-memory Python list (`INCIDENTS_DB`), capped at 1,000 records.

### 2.2 Streamlit Frontend (`opsmedic_dashboard/app.py`)

A real-time monitoring dashboard that polls the FastAPI agent.

- **Sidebar:** Agent health indicator (✅/❌), auto-refresh toggle, configurable refresh interval (1–60s), agent URL display.
- **Metrics Cards:** Total Incidents, Successful Remediations, Failed Remediations.
- **Incidents Table:** Columns — ID, Timestamp, Container, SLO, Root Cause, Action, Status.
- **Detail View:** Select any incident to see full metadata, diagnosis/justification, SLO info, and observability context.
- **Auto-Refresh:** Uses `st.rerun()` with a configurable sleep interval (default 5s).

### 2.3 Docker SDK Polling / Remediation Logic (`opsmedic_agent/remediation_executor/docker_actions.py`)

```python
def restart_container(container_id: str, allowed_container_names: list = None) -> (bool, str):
```

- Connects to the Docker daemon via `docker.from_env()`.
- Fetches the container by ID.
- **Safety check:** Validates the container name against an allowlist (default: `["buggy-app-v2"]`).
- Calls `container.restart()` if allowed.
- Returns `(success: bool, message: str)`.
- Handles `docker.errors.NotFound` and generic exceptions.

> **Note:** There is no post-restart verification (health check polling, metric comparison, etc.). The function only confirms the restart command was accepted by Docker.

### 2.4 LLM Prompt / Diagnosis Logic (`opsmedic_agent/ai_core/llm_client.py`)

**Entry point:** `diagnose_incident(incident_payload: dict) -> dict`

1. Loads LLM config from environment variables (`ACTIVE_LLM_PROVIDER`, API keys).
2. Constructs a prompt instructing the LLM to act as a "Senior SRE named OpsMedic."
3. Dispatches to the appropriate provider:
   - **Gemini** (`google.generativeai`, model `gemini-1.5-flash`)
   - **Llama** (HTTP POST to self-hosted endpoint)
   - **FastRouter** (HTTP POST to `https://go.fastrouter.ai/api/v1`)
4. Parses the LLM response as JSON with keys: `root_cause`, `recommended_action`, `justification`.
5. Actions the LLM can recommend: `RESTART`, `SCALE_OUT`, `IGNORE`.

**Prompt includes:** Container name/ID/image, breached SLO description, metrics snapshot, trace IDs, correlated logs.

> **Note:** This is a single-shot prompt, not a ReAct (Reasoning + Acting) loop. There is no multi-step tool-use or iterative reasoning chain — the LLM is called once and its JSON response is used directly.

---

## 3. Data Flow

### Step-by-Step: Container Degradation → LLM Diagnosis → Docker Remediation

```
┌─────────────────────────────────────────────────────────────────┐
│  1. PERCEIVE: buggy_app_v2 (Flask + OTel SDK)                  │
│     Exports metrics (memory, CPU), traces, logs                 │
│     → OTLP gRPC → otel-collector:4317                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
          ┌──────────────▼───────────────┐
          │  OpenTelemetry Collector      │
          │  Pipelines: traces, metrics,  │
          │  logs → processors (batch,    │
          │  memory_limiter, attributes)  │
          │  → exporters (logging,        │
          │    otlphttp → /webhook)       │
          └──────────────┬───────────────┘
                         │  HTTP POST to opsmedic-agent:8001/webhook
                         │
          ┌──────────────▼───────────────┐
          │  2. REASON: OpsMedic Agent    │
          │  (FastAPI /webhook)           │
          │  ├─ Validate Pydantic model   │
          │  ├─ Call diagnose_incident()  │
          │  │  → LLM prompt + API call   │
          │  └─ Receive JSON diagnosis    │
          └──────────────┬───────────────┘
                         │
          ┌──────────────▼───────────────┐
          │  3. ACT: Remediation          │
          │  If recommended_action ==     │
          │  "RESTART":                   │
          │  ├─ restart_container()       │
          │  ├─ Safety allowlist check    │
          │  └─ container.restart()       │
          └──────────────┬───────────────┘
                         │
          ┌──────────────▼───────────────┐
          │  4. STORE & REPORT            │
          │  ├─ Append to INCIDENTS_DB    │
          │  ├─ Return JSON response      │
          │  └─ Dashboard polls /incidents│
          └──────────────────────────────┘
```

### JSON Payload Structures

**Incident Payload (POST `/webhook` — from OTel Collector to Agent):**

```json
{
  "incident_id": "a_unique_uuid",
  "timestamp": "2024-01-15T10:30:45Z",
  "breached_slo": "Memory Utilization > 90% for 120 seconds",
  "container_info": {
    "id": "abc123def456",
    "name": "buggy-app-v2",
    "image": "buggy-app:v2"
  },
  "observability_context": {
    "metrics_snapshot": { "memory_usage": "95%", "cpu": "45%" },
    "trace_ids": ["trace-001", "trace-002"],
    "correlated_logs": "WARNING: Memory pressure detected...\nERROR: OOM killer invoked..."
  }
}
```

**LLM Diagnosis Response (internal — from `diagnose_incident()`):**

```json
{
  "root_cause": "Memory leak detected in caching layer due to unbounded dictionary growth",
  "recommended_action": "RESTART",
  "justification": "Restarting will reclaim leaked memory and restore service health"
}
```

**Webhook Response (returned to caller from POST `/webhook`):**

```json
{
  "status": "alert received",
  "incident_id": "a_unique_uuid",
  "diagnosis": {
    "root_cause": "Memory leak detected...",
    "recommended_action": "RESTART",
    "justification": "..."
  },
  "remediation": "SUCCESS"
}
```

**Stored Incident Record (in-memory, served via GET `/incidents`):**

```json
{
  "incident_id": "a_unique_uuid",
  "timestamp": "2024-01-15T10:30:45Z",
  "container_info": {
    "id": "abc123def456",
    "name": "buggy-app-v2",
    "image": "buggy-app:v2"
  },
  "breached_slo": "Memory Utilization > 90% for 120 seconds",
  "root_cause": "Memory leak detected...",
  "recommended_action": "RESTART",
  "remediation_status": "SUCCESS",
  "ai_justification": "Restarting will reclaim leaked memory..."
}
```

---

## 4. Current Limitations vs. Hackathon Goals

### 4.1 Three Specific API Triggers to Simulate Incidents

| Trigger | Implemented? | Endpoint / Details |
|---|---|---|
| **Memory Leak** | ✅ Yes | `GET /memory_leak` on buggy-app-v2 (port 8000). Each call appends 1 MB to a global list. OTel `container_memory_usage_bytes` gauge reports RSS via `psutil`. |
| **CPU / Crash Loop** | ✅ Partial | `GET /stress` on buggy-app-v2. Runs a CPU-intensive loop (1M iterations of `i**2`) with tracing. Generates CPU load but does **not** trigger a crash loop or container exit on its own. |
| **DB Latency** | ❌ No | No endpoint exists to simulate database latency. There is no database connection or simulated slow-query logic in `buggy_app_v2/app.py`. |

**Gap:** To fully demonstrate all 3 scenarios, we need:
- A `/db_latency` endpoint that simulates a slow database call (e.g., `time.sleep(2)` inside a traced span).
- A crash-loop mechanism (e.g., `os._exit(1)` endpoint or programmatic container exit) so Docker's restart policy triggers repeated restarts.

### 4.2 Post-Restart Verification

| Capability | Implemented? | Details |
|---|---|---|
| **Restart Container** | ✅ Yes | `restart_container()` calls Docker SDK `container.restart()`. |
| **Verify Fix After Restart** | ❌ No | The agent records `remediation_status: "SUCCESS"` if the restart **command** succeeds, but does **not** verify that the container came back healthy, that memory was reclaimed, or that the SLO breach was resolved. |

**Gap:** To verify fixes, we need:
- A post-restart health check loop (poll the container's `/health` endpoint or check `container.status`).
- Before/after metric comparison (e.g., memory before restart vs. memory after restart).
- Incident closure logic that marks the incident as `RESOLVED` only after SLO recovery is confirmed.

### 4.3 Other Notable Gaps

| Feature | Status |
|---|---|
| `SCALE_OUT` remediation | Referenced in prompt but **not implemented** in `docker_actions.py`. |
| `ROLLBACK` remediation | Mentioned in README but **not implemented** anywhere. |
| Persistent storage | In-memory only; all incidents are lost on agent restart. |
| OTel Collector → Agent webhook | Config routes raw OTel data to `/webhook`, but the payload format likely does **not** match the `IncidentPayload` Pydantic schema — a translation layer or custom SLO-breach detector is needed. |
| ReAct / multi-step reasoning | LLM is called once (single-shot). No iterative reasoning, tool use, or LangGraph integration yet. |

---

## 5. Dependencies

### opsmedic_agent (FastAPI Backend)

| Package | Purpose |
|---|---|
| `fastapi` | Web framework for webhook receiver and REST API |
| `uvicorn` | ASGI server to run FastAPI |
| `docker` | Docker SDK for Python — container restart logic |
| `google-generativeai` | Google Gemini LLM client |
| `requests` | HTTP client for Llama / FastRouter LLM APIs |
| `python-dotenv` | Load `.env` files for API keys |
| `openai` | OpenAI-compatible client (available but unused in current code) |

### opsmedic_dashboard (Streamlit Frontend)

| Package | Purpose |
|---|---|
| `streamlit` | Dashboard UI framework |
| `requests` | HTTP client to poll the agent API |
| `pandas` | DataFrame for incident table display |
| `python-dotenv` | Load `.env` files |

### buggy_app_v2 (Instrumented Target App)

| Package | Purpose |
|---|---|
| `flask` | Web framework for the target application |
| `gunicorn` | Production WSGI server |
| `opentelemetry-sdk` | Core OTel SDK |
| `opentelemetry-api` | OTel API |
| `opentelemetry-exporter-otlp` | OTLP gRPC exporter for traces, metrics, logs |
| `opentelemetry-instrumentation-flask` | Auto-instrumentation for Flask |
| `opentelemetry-distro` | OTel distribution bootstrapper |

### Infrastructure

| Component | Image / Config |
|---|---|
| OTel Collector | `otel/opentelemetry-collector:0.88.0` configured via `otel-collector-config.yaml` |
| Docker Compose | `version: '3.8'` — bridge network `opsmedic_net` |

---

## 6. Docker Compose Service Map

| Service | Port | Build Context | Depends On |
|---|---|---|---|
| `buggy-app-v2` | 8000 | `./opsmedic_project/buggy_app_v2` | otel-collector |
| `otel-collector` | 4317 (gRPC), 4318 (HTTP), 55681, 13133 | Pre-built image | — |
| `opsmedic-agent` | 8001 | `./opsmedic_project/opsmedic_agent` | otel-collector |
| `opsmedic-dashboard` | 8501 | `./opsmedic_project/opsmedic_dashboard` | opsmedic-agent |

### Environment Variables (via `.env`)

```bash
ACTIVE_LLM_PROVIDER=gemini        # gemini | llama | fastrouter
GEMINI_API_KEY=<your_key>
LLAMA_API_KEY=<your_key>
LLAMA_ENDPOINT=<url>
FASTRTR_API_KEY=<your_key>
FASTRTR_ENDPOINT=https://go.fastrouter.ai/api/v1
OPS_AGENT_PORT=8001                # Optional override
```

---

*Generated on 2026-02-20. Based on commit history up to this date.*
