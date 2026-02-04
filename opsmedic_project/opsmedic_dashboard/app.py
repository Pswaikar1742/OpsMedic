import streamlit as st
import requests
import pandas as pd
import time
import json

# Set page title
st.set_page_config(page_title="OpsMedic Autonomous SRE Dashboard")
st.title("OpsMedic Autonomous SRE Dashboard")

# Function to fetch incidents from opsmedic-agent
def fetch_incidents(agent_url):
    try:
        response = requests.get(f"{agent_url}/incidents")
        response.raise_for_status()
        return response.json().get("incidents", [])
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching incidents: {e}")
        return []

# Refresh button
if st.button("Refresh Data"):
    st.experimental_rerun()

# Display live container status
st.header("Live Container Status")
# Placeholder for container status (to be updated in the future)
st.write("buggy-app-v2: RUNNING")

# Display recent incidents
st.header("Recent Incidents")
agent_url = "http://opsmedic-agent:8001"
incidents = fetch_incidents(agent_url)

if incidents:
    # Convert incidents to a DataFrame for display
    df = pd.DataFrame(incidents)
    st.dataframe(df)
else:
    st.write("No incidents to display.")