from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel, Field, validator
import logging
import os
from typing import Optional, Dict, Any
from ai_core.llm_client import diagnose_incident
from remediation_executor.docker_actions import restart_container

# Initialize FastAPI app
app = FastAPI(title="OpsMedic Agent", version="1.0.0")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opsmedic-agent")

# API Key validation (optional)
AGENT_API_KEY = os.getenv("AGENT_API_KEY", None)

# Global in-memory database for storing incidents (limit to 1000 records)
INCIDENTS_DB = []
MAX_INCIDENTS = 1000

# Pydantic models for request validation
class ContainerInfo(BaseModel):
    id: str = Field(..., min_length=1, description="Container ID")
    name: str = Field(..., min_length=1, description="Container name")
    image: Optional[str] = Field(None, description="Container image")

class ObservabilityContext(BaseModel):
    metrics_snapshot: Optional[Dict[str, Any]] = Field(None, description="Metrics snapshot")
    trace_ids: Optional[list] = Field(default_factory=list, description="Trace IDs")
    correlated_logs: Optional[str] = Field(None, description="Correlated logs")

class IncidentPayload(BaseModel):
    incident_id: str = Field(..., min_length=1, description="Unique incident ID")
    timestamp: str = Field(..., description="ISO8601 timestamp")
    breached_slo: str = Field(..., min_length=1, description="Breached SLO description")
    container_info: ContainerInfo
    observability_context: ObservabilityContext

    @validator('incident_id')
    def validate_incident_id(cls, v):
        if len(v) < 1 or len(v) > 256:
            raise ValueError('incident_id must be between 1 and 256 characters')
        return v

def validate_api_key(request: Request) -> bool:
    """Validate the API key if configured."""
    if not AGENT_API_KEY:
        return True
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        logger.warning("Request missing Bearer token")
        return False
    
    token = auth_header[7:]
    if token != AGENT_API_KEY:
        logger.warning("Invalid API key provided")
        return False
    
    return True

@app.post("/webhook")
async def webhook(request: Request):
    """Receive incident alerts from OpenTelemetry Collector."""
    # Validate API key
    if not validate_api_key(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    try:
        incident_payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse request JSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )
    
    # Validate payload structure
    try:
        validated_payload = IncidentPayload(**incident_payload)
    except Exception as e:
        logger.error(f"Payload validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payload validation error: {str(e)}"
        )
    
    logger.info(f"Received validated alert: {validated_payload.incident_id}")
    
    # Diagnose the incident using the LLM
    diagnosis = diagnose_incident(validated_payload.dict())
    root_cause = diagnosis.get("root_cause", "Unknown")
    recommended_action = diagnosis.get("recommended_action", "IGNORE")
    justification = diagnosis.get("justification", "No justification provided.")
    
    logger.info(f"Diagnosis: Root Cause: {root_cause}, Action: {recommended_action}")
    
    # Perform remediation if recommended action is RESTART
    remediation_status = "No action taken."
    if recommended_action == "RESTART":
        container_id = validated_payload.container_info.id
        container_name = validated_payload.container_info.name
        success, message = restart_container(container_id, allowed_container_names=["buggy-app-v2"])
        remediation_status = "SUCCESS" if success else "FAILED"
        logger.info(f"Remediation result for {container_name}: {message}")
    
    # Store the incident in the in-memory database
    incident_record = {
        "incident_id": validated_payload.incident_id,
        "timestamp": validated_payload.timestamp,
        "container_info": validated_payload.container_info.dict(),
        "breached_slo": validated_payload.breached_slo,
        "root_cause": root_cause,
        "recommended_action": recommended_action,
        "remediation_status": remediation_status,
        "ai_justification": justification
    }
    INCIDENTS_DB.append(incident_record)
    
    # Enforce size limit
    if len(INCIDENTS_DB) > MAX_INCIDENTS:
        INCIDENTS_DB.pop(0)
    
    return {
        "status": "alert received",
        "incident_id": validated_payload.incident_id,
        "diagnosis": diagnosis,
        "remediation": remediation_status
    }

@app.get("/incidents")
async def get_incidents(request: Request, limit: int = 100):
    """Retrieve recent incidents."""
    if not validate_api_key(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )
    
    # Return the last `limit` incidents
    return {
        "incidents": INCIDENTS_DB[-limit:],
        "total": len(INCIDENTS_DB)
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "incidents_stored": len(INCIDENTS_DB)}

@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "OpsMedic Agent",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/webhook (POST)",
            "incidents": "/incidents (GET)",
            "health": "/health (GET)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("OPS_AGENT_PORT", 8001))
    logger.info(f"Starting OpsMedic Agent on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)