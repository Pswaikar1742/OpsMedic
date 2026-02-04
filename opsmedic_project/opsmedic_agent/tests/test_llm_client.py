import unittest
from unittest.mock import patch, MagicMock
from opsmedic_agent.ai_core.llm_client import diagnose_incident, _construct_prompt

class TestLLMClient(unittest.TestCase):

    @patch("opsmedic_agent.ai_core.llm_client._call_fastrouter_api")
    def test_diagnose_incident_fastrouter(self, mock_fastrouter):
        # Mock response from FastRouter
        mock_fastrouter.return_value = {
            "root_cause": "Memory leak detected in application",
            "recommended_action": "RESTART",
            "justification": "To reclaim memory and prevent further degradation."
        }

        # Sample incident payload
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

        # Set active LLM provider to FastRouter
        with patch("opsmedic_agent.ai_core.llm_client.load_llm_config", return_value={
            "active_llm_provider": "fastrouter_claude",
            "fastrouter_api_key": "test_key",
            "fastrouter_endpoint": "https://test.endpoint"
        }):
            result = diagnose_incident(incident_payload)

        # Assertions
        self.assertEqual(result["root_cause"], "Memory leak detected in application")
        self.assertEqual(result["recommended_action"], "RESTART")
        self.assertEqual(result["justification"], "To reclaim memory and prevent further degradation.")

    def test_construct_prompt(self):
        # Sample incident payload
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

        # Generate prompt
        prompt = _construct_prompt(incident_payload)

        # Assertions
        self.assertIn("Memory Utilization > 90% for 2 mins", prompt)
        self.assertIn("buggy-app-v2", prompt)
        self.assertIn("Out of memory error", prompt)

if __name__ == "__main__":
    unittest.main()