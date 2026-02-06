import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_core.llm_client import diagnose_incident, _construct_prompt, load_llm_config


class TestLLMClient(unittest.TestCase):

    def test_construct_prompt(self):
        """Test that prompt construction includes all relevant incident data."""
        incident_payload = {
            "container_info": {
                "id": "12345",
                "name": "buggy-app-v2",
                "image": "buggy-app:v2"
            },
            "breached_slo": "Memory Utilization > 90% for 2 mins",
            "observability_context": {
                "metrics_snapshot": {"memory_usage": "95%"},
                "trace_ids": ["trace123"],
                "correlated_logs": "Out of memory error"
            }
        }

        prompt = _construct_prompt(incident_payload)
        
        self.assertIn("Memory Utilization > 90% for 2 mins", prompt)
        self.assertIn("buggy-app-v2", prompt)
        self.assertIn("Out of memory error", prompt)
        self.assertIn("RESTART", prompt)

    @patch("ai_core.llm_client.load_llm_config")
    @patch("ai_core.llm_client._call_fastrouter_api")
    def test_diagnose_incident_fastrouter(self, mock_fastrouter, mock_config):
        """Test incident diagnosis using FastRouter provider."""
        mock_config.return_value = {
            "active_llm_provider": "fastrouter",
            "fastrouter_api_key": "test_key",
            "fastrouter_endpoint": "https://test.endpoint",
            "gemini_api_key": None,
            "llama_api_key": None,
            "llama_endpoint": None
        }
        
        mock_fastrouter.return_value = {
            "root_cause": "Memory leak detected in application",
            "recommended_action": "RESTART",
            "justification": "To reclaim memory and prevent further degradation."
        }

        incident_payload = {
            "container_info": {
                "id": "12345",
                "name": "buggy-app-v2",
                "image": "buggy-app:v2"
            },
            "breached_slo": "Memory Utilization > 90% for 2 mins",
            "observability_context": {
                "metrics_snapshot": {"memory_usage": "95%"},
                "trace_ids": ["trace123"],
                "correlated_logs": "Out of memory error"
            }
        }

        result = diagnose_incident(incident_payload)

        self.assertEqual(result["root_cause"], "Memory leak detected in application")
        self.assertEqual(result["recommended_action"], "RESTART")
        self.assertIn("justification", result)
        mock_fastrouter.assert_called_once()

    @patch("ai_core.llm_client.load_llm_config")
    @patch("ai_core.llm_client._call_gemini_api")
    def test_diagnose_incident_gemini(self, mock_gemini, mock_config):
        """Test incident diagnosis using Gemini provider."""
        mock_config.return_value = {
            "active_llm_provider": "gemini",
            "gemini_api_key": "test_gemini_key",
            "fastrouter_api_key": None,
            "fastrouter_endpoint": None,
            "llama_api_key": None,
            "llama_endpoint": None
        }
        
        mock_gemini.return_value = {
            "root_cause": "High memory usage due to inefficient caching",
            "recommended_action": "RESTART",
            "justification": "Restart will clear caches and reduce memory footprint."
        }

        incident_payload = {
            "container_info": {
                "id": "67890",
                "name": "buggy-app-v2",
                "image": "buggy-app:v2"
            },
            "breached_slo": "P99 Latency > 1.5s",
            "observability_context": {
                "metrics_snapshot": {"p99_latency": "1.8s"},
                "trace_ids": ["trace456"],
                "correlated_logs": "Slow response times"
            }
        }

        result = diagnose_incident(incident_payload)

        self.assertEqual(result["root_cause"], "High memory usage due to inefficient caching")
        self.assertEqual(result["recommended_action"], "RESTART")
        mock_gemini.assert_called_once()

    @patch("ai_core.llm_client.load_llm_config")
    @patch("ai_core.llm_client._call_llama_api")
    def test_diagnose_incident_llama(self, mock_llama, mock_config):
        """Test incident diagnosis using Llama provider."""
        mock_config.return_value = {
            "active_llm_provider": "llama",
            "llama_api_key": "test_llama_key",
            "llama_endpoint": "http://localhost:8000",
            "gemini_api_key": None,
            "fastrouter_api_key": None,
            "fastrouter_endpoint": None
        }
        
        mock_llama.return_value = {
            "root_cause": "Database connection pool exhausted",
            "recommended_action": "SCALE_OUT",
            "justification": "Scale out to increase available resources."
        }

        incident_payload = {
            "container_info": {
                "id": "99999",
                "name": "buggy-app-v2",
                "image": "buggy-app:v2"
            },
            "breached_slo": "Error Rate > 5%",
            "observability_context": {
                "metrics_snapshot": {"error_rate": "7%"},
                "trace_ids": ["trace789"],
                "correlated_logs": "Connection timeout errors"
            }
        }

        result = diagnose_incident(incident_payload)

        self.assertEqual(result["recommended_action"], "SCALE_OUT")
        mock_llama.assert_called_once()

    @patch("ai_core.llm_client.load_llm_config")
    def test_invalid_provider(self, mock_config):
        """Test diagnosis with invalid provider returns error."""
        mock_config.return_value = {
            "active_llm_provider": "invalid_provider",
            "gemini_api_key": None,
            "llama_api_key": None,
            "llama_endpoint": None,
            "fastrouter_api_key": None,
            "fastrouter_endpoint": None
        }

        incident_payload = {
            "container_info": {
                "id": "12345",
                "name": "buggy-app-v2",
                "image": "buggy-app:v2"
            },
            "breached_slo": "Memory Utilization > 90%",
            "observability_context": {
                "metrics_snapshot": {"memory_usage": "95%"},
                "trace_ids": ["trace123"],
                "correlated_logs": "Out of memory"
            }
        }

        result = diagnose_incident(incident_payload)
        
        self.assertIn("error", result)
        self.assertIn("Invalid LLM provider", result["error"])

    def test_load_llm_config(self):
        """Test that LLM config loads with proper defaults."""
        with patch.dict("os.environ", {"ACTIVE_LLM_PROVIDER": "GEMINI"}):
            config = load_llm_config()
            self.assertEqual(config["active_llm_provider"].lower(), "gemini")


if __name__ == "__main__":
    unittest.main()
