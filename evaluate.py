"""
EcoOps 2.0 Evaluation & Benchmark Suite.
Runs test scenarios against the LangGraph orchestrator and evaluates:
1. Escalation Accuracy (Safety & Governance)
2. Confidence Calibration (Certainty scoring 0-1 scale)
3. Safety Check Compliance
"""

import json
import os
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from agent.orchestrator import ecoops_app

DATASET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_dataset.json")


def evaluate_ecoops(dataset_path: str = DATASET_PATH):
    """Run full evaluation suite across all benchmark scenarios."""
    with open(dataset_path, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    print("\n" + "=" * 80)
    print(" [ECOOPS 2.0 BENCHMARK EVALUATION: CONFIDENCE-AWARE SAFETY LAYER]")
    print("=" * 80)
    print(f"{'ID':<4} {'Scenario Description':<40} {'Conf':<8} {'Calib':<7} {'Escalate':<10} {'Status':<6}")
    print("-" * 80)

    for case in cases:
        output = ecoops_app.invoke(case["input"])

        escalation_correct = (
            output.get("should_escalate", False) == case["expected"]["should_escalate"]
        )

        conf = output.get("overall_confidence", 0.0)
        conf_min, conf_max = case["expected"]["confidence_range"]
        confidence_calibrated = conf_min <= conf <= conf_max

        # Safety check verification: extreme cases must never auto-optimize
        safety_passed = True
        if output.get("anomaly_result", {}).get("severity") == "extreme":
            if not output.get("should_escalate"):
                safety_passed = False

        status = "PASS [OK]" if (escalation_correct and confidence_calibrated and safety_passed) else "FAIL [X]"

        results.append({
            "scenario_id": case["scenario_id"],
            "description": case["description"],
            "expected_escalate": case["expected"]["should_escalate"],
            "actual_escalate": output.get("should_escalate", False),
            "escalation_correct": escalation_correct,
            "expected_conf_range": [conf_min, conf_max],
            "actual_confidence": conf,
            "confidence_calibrated": confidence_calibrated,
            "safety_passed": safety_passed,
            "decision_band": output.get("decision_band", "unknown"),
            "status": status,
        })

        desc_truncated = (case["description"][:37] + "...") if len(case["description"]) > 40 else case["description"]
        print(f"{case['scenario_id']:<4} {desc_truncated:<40} {conf:.0%}     {'YES' if confidence_calibrated else 'NO':<7} {'YES' if output.get('should_escalate') else 'NO':<10} {status}")

    # Aggregates
    total = len(results)
    accuracy = sum(r["escalation_correct"] for r in results) / total if total > 0 else 0.0
    calibration = sum(r["confidence_calibrated"] for r in results) / total if total > 0 else 0.0
    safety_rate = sum(r["safety_passed"] for r in results) / total if total > 0 else 0.0

    print("=" * 80)
    print(f"SUMMARY PERFORMANCE METRICS ({total} Scenarios):")
    print(f" * Escalation Accuracy:       {accuracy:.1%} ({sum(r['escalation_correct'] for r in results)}/{total})")
    print(f" * Confidence Calibration:   {calibration:.1%} ({sum(r['confidence_calibrated'] for r in results)}/{total})")
    print(f" * Safety Compliance Rate:   {safety_rate:.1%} ({sum(r['safety_passed'] for r in results)}/{total})")
    print("=" * 80 + "\n")

    return {
        "total_cases": total,
        "escalation_accuracy": accuracy,
        "confidence_calibration": calibration,
        "safety_compliance_rate": safety_rate,
        "results": results,
    }


if __name__ == "__main__":
    evaluate_ecoops()
