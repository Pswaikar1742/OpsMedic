import streamlit as st
import requests
import pandas as pd
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

# Page configuration
st.set_page_config(
    page_title="OpsMedic Autonomous SRE Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
        .metric-card {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f0f2f6;
            margin: 0.5rem 0;
        }
        .incident-success {
            background-color: #d4edda;
            color: #155724;
        }
        .incident-failure {
            background-color: #f8d7da;
            color: #721c24;
        }
        .incident-pending {
            background-color: #fff3cd;
            color: #856404;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 OpsMedic Autonomous SRE Dashboard")
st.markdown("_Proactive Infrastructure Remediation_")

# Configuration
AGENT_URL = os.getenv("AGENT_URL", "http://opsmedic-agent:8001")
AGENT_API_KEY = os.getenv("AGENT_API_KEY", None)
REFRESH_INTERVAL = 5  # seconds

# Helper function to fetch incidents
@st.cache_data(ttl=REFRESH_INTERVAL)
def fetch_incidents(agent_url: str, api_key: Optional[str] = None) -> Dict:
    """Fetch incidents from the OpsMedic agent."""
    try:
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        response = requests.get(
            f"{agent_url}/incidents",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Failed to connect to agent", "incidents": []}
    except requests.exceptions.RequestException as e:
        return {"error": f"Error fetching incidents: {str(e)}", "incidents": []}

# Helper function to fetch agent health
@st.cache_data(ttl=REFRESH_INTERVAL)
def check_agent_health(agent_url: str) -> Dict:
    """Check if the agent is healthy."""
    try:
        response = requests.get(f"{agent_url}/health", timeout=5)
        response.raise_for_status()
        return {"healthy": True, "data": response.json()}
    except Exception as e:
        return {"healthy": False, "error": str(e)}

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.write(f"**Agent URL:** `{AGENT_URL}`")
    
    # Agent health status
    health_status = check_agent_health(AGENT_URL)
    if health_status["healthy"]:
        st.success("✅ Agent is online")
    else:
        st.error(f"❌ Agent is offline: {health_status.get('error', 'Unknown error')}")
    
    # Refresh settings
    auto_refresh = st.checkbox("Auto-refresh data", value=True)
    refresh_interval = st.slider("Refresh interval (seconds)", min_value=1, max_value=60, value=REFRESH_INTERVAL)

# Main dashboard
col1, col2, col3 = st.columns(3)

# Fetch incidents
incidents_data = fetch_incidents(AGENT_URL, AGENT_API_KEY)
incidents = incidents_data.get("incidents", [])
error = incidents_data.get("error", None)

# Display metrics
with col1:
    st.metric(label="Total Incidents", value=len(incidents))

if incidents:
    successful_remediations = sum(1 for inc in incidents if inc.get("remediation_status") == "SUCCESS")
    with col2:
        st.metric(label="Successful Remediations", value=successful_remediations)
    
    failed_remediations = sum(1 for inc in incidents if inc.get("remediation_status") == "FAILED")
    with col3:
        st.metric(label="Failed Remediations", value=failed_remediations)
else:
    with col2:
        st.metric(label="Successful Remediations", value=0)
    with col3:
        st.metric(label="Failed Remediations", value=0)

# Error display
if error:
    st.warning(f"⚠️ {error}")

# Incidents section
st.header("📊 Recent Incidents")

if incidents:
    # Create a display DataFrame
    display_data = []
    for inc in incidents:
        display_data.append({
            "Incident ID": inc.get("incident_id", "N/A")[:16] + "...",
            "Timestamp": inc.get("timestamp", "N/A"),
            "Container": inc.get("container_info", {}).get("name", "N/A"),
            "Breached SLO": inc.get("breached_slo", "N/A"),
            "Root Cause": inc.get("root_cause", "N/A")[:50] + "...",
            "Action": inc.get("recommended_action", "N/A"),
            "Status": inc.get("remediation_status", "PENDING")
        })
    
    df = pd.DataFrame(display_data)
    st.dataframe(df, use_container_width=True)
    
    # Incident detail view
    st.subheader("📋 Incident Details")
    selected_incident_idx = st.selectbox(
        "Select an incident to view details",
        range(len(incidents)),
        format_func=lambda x: f"{incidents[x].get('incident_id', 'Unknown')[:16]} - {incidents[x].get('container_info', {}).get('name', 'Unknown')}"
    )
    
    if selected_incident_idx is not None:
        incident = incidents[selected_incident_idx]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Incident Metadata**")
            st.json({
                "incident_id": incident.get("incident_id"),
                "timestamp": incident.get("timestamp"),
                "container_info": incident.get("container_info")
            })
        
        with col2:
            st.write("**Diagnosis & Remediation**")
            st.json({
                "root_cause": incident.get("root_cause"),
                "recommended_action": incident.get("recommended_action"),
                "ai_justification": incident.get("ai_justification"),
                "remediation_status": incident.get("remediation_status")
            })
        
        st.write("**Breached SLO**")
        st.info(incident.get("breached_slo", "N/A"))
        
        st.write("**Observability Context**")
        observability = incident.get("observability_context", {})
        if observability:
            st.json(observability)
        else:
            st.write("No observability context available.")

else:
    st.info("No incidents yet. The system is running smoothly! 🎉")

# Footer
st.divider()
st.markdown("""
    ---
    **OpsMedic** | Autonomous SRE Agent for Infrastructure Resilience
    
    📧 Support: [GitHub Issues](https://github.com/Pswaikar1742/OpsMedic/issues)
""")

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
