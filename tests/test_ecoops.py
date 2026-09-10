"""
Comprehensive Unit & Integration Test Suite for EcoOps 2.0.
Verifies LangGraph State Machine, FastMCP Tools, RAG Retriever,
Confidence Scoring Calibration, and FastAPI Endpoints.
"""

import unittest
import os
from fastapi.testclient import TestClient

from main import app
from agent.orchestrator import ecoops_app
from tools.mcp_tools import (
    detect_anomaly,
    retrieve_policies,
    calculate_emissions_impact,
    alert_facilities_team,
    find_historical_precedent,
)
from evaluate import evaluate_ecoops


class TestEcoOpsCore(unittest.TestCase):
    """Test MCP Tools and core computational units."""

    def test_detect_anomaly_moderate(self):
        result = detect_anomaly(
            current_value=11500,
            baseline_value=10000,
            metric_type="energy",
            context={"sensor_status": "operational", "days_since_calibration": 45}
        )
        self.assertTrue(result["is_anomaly"])
        self.assertEqual(result["severity"], "moderate")
        self.assertAlmostEqual(result["percent_change"], 15.0, places=1)
        self.assertGreaterEqual(result["confidence"], 0.85)

    def test_detect_anomaly_extreme_outlier(self):
        result = detect_anomaly(
            current_value=38000,
            baseline_value=10000,
            metric_type="energy",
            context={"sensor_status": "operational", "time": "02:47"}
        )
        self.assertTrue(result["is_anomaly"])
        self.assertEqual(result["severity"], "extreme")
        self.assertAlmostEqual(result["percent_change"], 280.0, places=1)
        # Outlier penalty applied
        self.assertLessEqual(result["confidence"], 0.60)

    def test_detect_anomaly_sensor_uncertainty(self):
        result = detect_anomaly(
            current_value=15000,
            baseline_value=11100,
            metric_type="water",
            context={"sensor_status": "recently_replaced", "days_since_calibration": 2}
        )
        self.assertTrue(result["is_anomaly"])
        # Recently replaced sensor receives penalty
        self.assertLessEqual(result["confidence"], 0.70)

    def test_retrieve_policies_rag(self):
        rag_res = retrieve_policies(
            query="Academic Block A summer HVAC optimization schedule",
            anomaly_type="moderate",
            top_k=3
        )
        self.assertGreater(len(rag_res["documents"]), 0)
        self.assertGreater(len(rag_res["sources"]), 0)
        self.assertGreaterEqual(rag_res["confidence"], 0.65)
        # Check source presence
        sources_str = " ".join(rag_res["sources"]).lower()
        self.assertTrue("summer" in sources_str or "energy" in sources_str)

    def test_calculate_emissions_impact(self):
        impact = calculate_emissions_impact(energy_kwh_saved=1200, water_liters_saved=500)
        self.assertGreater(impact["co2_kg_saved"], 800)
        self.assertGreater(impact["cost_savings_inr"], 4000)
        self.assertEqual(impact["confidence"], 0.85)

    def test_alert_facilities_team(self):
        alert = alert_facilities_team(
            building="Chemistry Lab",
            issue_type="extreme",
            severity="extreme",
            data_summary={"percent_change": 380.0},
            confidence=0.28
        )
        self.assertTrue(alert["alert_id"].startswith("ALERT-"))
        self.assertEqual(alert["status"], "sent")
        self.assertEqual(alert["expected_response_time"], "15 minutes")

    def test_find_historical_precedent_match(self):
        history = find_historical_precedent(
            metric_type="energy",
            percent_change=15.0,
            month="June"
        )
        self.assertTrue(history["precedent_found"])
        self.assertGreaterEqual(history["num_similar_cases"], 5)
        self.assertGreaterEqual(history["confidence"], 0.75)

    def test_find_historical_precedent_novel(self):
        history = find_historical_precedent(
            metric_type="energy",
            percent_change=380.0,
            month="March"
        )
        self.assertFalse(history["precedent_found"])
        self.assertLessEqual(history["confidence"], 0.30)


class TestLangGraphScenarios(unittest.TestCase):
    """Test LangGraph State Machine across the 3 core Hackathon Scenarios."""

    def test_scenario_a_auto_implement(self):
        state = ecoops_app.invoke({
            "query": "Energy consumption increased by 15%",
            "metric_data": {
                "current": 12500,
                "baseline": 10870,
                "type": "energy",
                "month": "June",
                "building": "Academic Block A",
                "context": {"sensor_status": "operational", "days_since_calibration": 45}
            }
        })
        self.assertFalse(state["should_escalate"])
        self.assertEqual(state["decision_band"], "auto_act")
        self.assertGreaterEqual(state["overall_confidence"], 0.75)
        self.assertIn("trace_log", state)
        self.assertGreaterEqual(len(state["trace_log"]), 5)

    def test_scenario_b_warn_and_monitor(self):
        state = ecoops_app.invoke({
            "query": "Water usage up 35%",
            "metric_data": {
                "current": 15000,
                "baseline": 11100,
                "type": "water",
                "month": "April",
                "building": "Hostel C",
                "context": {"sensor_status": "recently_replaced", "days_since_calibration": 2}
            }
        })
        self.assertFalse(state["should_escalate"])
        self.assertEqual(state["decision_band"], "warn")
        self.assertGreaterEqual(state["overall_confidence"], 0.50)
        self.assertLess(state["overall_confidence"], 0.75)

    def test_scenario_c_immediate_escalation(self):
        state = ecoops_app.invoke({
            "query": "Massive energy spike at 2 AM",
            "metric_data": {
                "current": 38000,
                "baseline": 10000,
                "type": "energy",
                "month": "March",
                "building": "Chemistry Lab",
                "context": {"sensor_status": "operational", "time": "02:47"}
            }
        })
        self.assertTrue(state["should_escalate"])
        self.assertEqual(state["decision_band"], "escalate")
        self.assertLess(state["overall_confidence"], 0.50)
        self.assertTrue(any("ESCALATED" in str(r.get("title", "")) for r in state["recommendations"]))


class TestBenchmarkAndAPI(unittest.TestCase):
    """Test full 20-scenario benchmark suite and FastAPI client."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_benchmark_suite_100_percent(self):
        results = evaluate_ecoops()
        self.assertEqual(results["escalation_accuracy"], 1.0)
        self.assertEqual(results["confidence_calibration"], 1.0)
        self.assertEqual(results["safety_compliance_rate"], 1.0)
        self.assertEqual(results["total_cases"], 20)

    def test_api_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")

    def test_api_scenarios(self):
        res = self.client.get("/api/scenarios")
        self.assertEqual(res.status_code, 200)
        scenarios = res.json()
        self.assertGreaterEqual(len(scenarios), 3)

    def test_api_analyze(self):
        res = self.client.post("/api/analyze", json={
            "query": "Test query",
            "metric_data": {
                "current": 12000,
                "baseline": 10000,
                "type": "energy",
                "month": "June",
                "building": "Academic Block A",
                "context": {"sensor_status": "operational"}
            }
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("overall_confidence", data["result"])

    def test_api_alerts_and_ack(self):
        alerts = self.client.get("/api/alerts").json()
        self.assertIsInstance(alerts, list)
        if len(alerts) > 0:
            aid = alerts[0]["alert_id"]
            ack_res = self.client.post(f"/api/alerts/{aid}/acknowledge", json={
                "notes": "Test acknowledgement note"
            })
            self.assertEqual(ack_res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
