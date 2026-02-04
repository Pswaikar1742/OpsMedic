from fastapi import FastAPI, Request
import logging
from ai_core.llm_client import diagnose_incident
from remediation_executor.docker_actions import restart_container

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opsmedic-agent")

# Global in-memory database for storing incidents
INCIDENTS_DB = []

@app.post("/alert")
async def alert(request: Request):
    incident_payload = await request.json()
    logger.info(f"Received alert: {incident_payload}")

    # Diagnose the incident using the LLM
    diagnosis = diagnose_incident(incident_payload)
    root_cause = diagnosis.get("root_cause", "Unknown")
    recommended_action = diagnosis.get("recommended_action", "IGNORE")
    justification = diagnosis.get("justification", "No justification provided.")

    logger.info(f"Diagnosis: Root Cause: {root_cause}, Recommended Action: {recommended_action}, Justification: {justification}")

    # Perform remediation if recommended action is RESTART
    remediation_status = "No action taken."
    if recommended_action == "RESTART":
        container_id = incident_payload["container_info"]["id"]
        container_name = incident_payload["container_info"]["name"]
        success, message = restart_container(container_id, allowed_container_names=["buggy-app-v2"])
        remediation_status = "SUCCESS" if success else "FAILED"
        logger.info(f"Remediation result for container {container_name}: {message}")

    # Store the incident in the in-memory database
    incident_record = {
        "incident_id": incident_payload.get("incident_id"),
        "timestamp": incident_payload.get("timestamp"),
        "container_info": incident_payload.get("container_info"),
        "breached_slo": incident_payload.get("breached_slo"),
        "root_cause": root_cause,
        "recommended_action": recommended_action,
        "remediation_status": remediation_status,
        "ai_justification": justification
    }
    INCIDENTS_DB.append(incident_record)

    return {"status": "alert received", "diagnosis": diagnosis, "remediation": remediation_status}

@app.get("/incidents")
def get_incidents():
    return {"incidents": INCIDENTS_DB}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)