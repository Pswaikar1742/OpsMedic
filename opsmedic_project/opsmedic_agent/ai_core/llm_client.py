import os
import logging
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from openai import OpenAI

# Load environment variables
load_dotenv()

def load_llm_config():
    """Load LLM configuration from environment variables."""
    config = {
        "gemini_api_key": os.getenv("GEMINI_API_KEY"),
        "llama_api_key": os.getenv("LLAMA_API_KEY"),
        "llama_endpoint": os.getenv("LLAMA_ENDPOINT"),
        "active_llm_provider": os.getenv("ACTIVE_LLM_PROVIDER", "gemini"),
        "fastrouter_api_key": os.getenv("FASTRTR_API_KEY"),
        "fastrouter_endpoint": os.getenv("FASTRTR_ENDPOINT", "https://go.fastrouter.ai/api/v1")
    }
    logging.debug(f"Loaded LLM configuration: {config}")
    return config

def _construct_prompt(incident_payload: dict) -> str:
    """Construct a detailed prompt for the LLM based on the incident payload."""
    prompt = (
        f"You are a Senior Site Reliability Engineer (SRE) named OpsMedic. Your task is to analyze system incidents and recommend the best course of action.\n"
        f"An incident has occurred for container '{incident_payload['container_info']['name']}' (ID: {incident_payload['container_info']['id']}, Image: {incident_payload['container_info']['image']}).\n"
        f"**SLO Breached:** {incident_payload['breached_slo']}\n"
        f"**Observability Context:**\n"
        f"Metrics Snapshot: {incident_payload['observability_context'].get('metrics_snapshot', 'N/A')}\n"
        f"Trace IDs: {incident_payload['observability_context'].get('trace_ids', 'N/A')}\n"
        f"Correlated Logs: {incident_payload['observability_context'].get('correlated_logs', 'N/A')}\n\n"
        f"Analyze the provided context and determine the most likely root cause. Then, recommend one of the following actions in JSON format: 'RESTART', 'SCALE_OUT', 'IGNORE'. If 'RESTART', provide a brief justification.\n"
        f"Example Response:\n"
        f"{{\"root_cause\": \"Likely memory leak due to X\", \"recommended_action\": \"RESTART\", \"justification\": \"To reclaim leaked memory and restore service health.\"}}"
    )
    return prompt

def _call_gemini_api(prompt: str, api_key: str) -> dict:
    """Call the Gemini API with the given prompt."""
    genai.configure(api_key=api_key)
    try:
        response = genai.generate_text(prompt=prompt)
        return response
    except Exception as e:
        logging.error(f"Error calling Gemini API: {e}")
        return {"error": str(e)}

def _call_llama_api(prompt: str, api_key: str, endpoint: str) -> dict:
    """Call the Llama API with the given prompt."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"prompt": prompt}
    try:
        response = requests.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error calling Llama API: {e}")
        return {"error": str(e)}

def _call_fastrouter_api(prompt: str, api_key: str, endpoint: str) -> dict:
    """Call the FastRouter API with the given prompt."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"prompt": prompt}
    try:
        response = requests.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error calling FastRouter API: {e}")
        return {"error": str(e)}

def diagnose_incident(incident_payload: dict) -> dict:
    """Diagnose the incident using the configured LLM provider."""
    config = load_llm_config()
    prompt = _construct_prompt(incident_payload)

    if config["active_llm_provider"] == "gemini":
        return _call_gemini_api(prompt, config["gemini_api_key"])
    elif config["active_llm_provider"] == "llama":
        return _call_llama_api(prompt, config["llama_api_key"], config["llama_endpoint"])
    elif config["active_llm_provider"] == "fastrouter":
        return _call_fastrouter_api(prompt, config["fastrouter_api_key"], config["fastrouter_endpoint"])
    else:
        logging.error("Invalid LLM provider specified in configuration.")
        return {"error": "Invalid LLM provider"}