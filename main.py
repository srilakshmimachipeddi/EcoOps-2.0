"""
FastAPI Backend Server for EcoOps 2.0.
Provides RESTful APIs for anomaly analysis, LangGraph execution,
escalation queues, RAG knowledge browsing, and benchmark evaluation.
"""

import os
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.orchestrator import ecoops_app
from evaluate import evaluate_ecoops
from rag.retriever import get_retriever, KB_DIR
from tools.mcp_tools import ALERTS_LOG_PATH

app = FastAPI(
    title="EcoOps 2.0 API",
    description="Confidence-Aware Campus Sustainability Agent API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")

# In-memory alert status store for acknowledgements
_acknowledged_alerts = {}

class AnalyzeRequest(BaseModel):
    query: str
    metric_data: Dict[str, Any]

class AcknowledgeRequest(BaseModel):
    notes: Optional[str] = "Physical inspection dispatched by facilities coordinator"
    officer: Optional[str] = "Head of Campus Facilities"

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "EcoOps 2.0",
        "timestamp": datetime.now().isoformat(),
        "architecture": "LangGraph (6 Nodes + Conditional Router) + FastMCP Tools"
    }

@app.post("/api/analyze")
def analyze_anomaly(req: AnalyzeRequest):
    """Execute LangGraph orchestrator state machine."""
    try:
        input_data = {
            "query": req.query,
            "metric_data": req.metric_data
        }
        result = ecoops_app.invoke(input_data)
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {str(e)}")

@app.get("/api/scenarios")
def get_scenarios():
    """Return pre-configured benchmark scenarios for instant demo switching."""
    return [
        {
            "id": "scenario_a",
            "name": "Scenario A: Summer Cooling Surge (High Conf)",
            "building": "Academic Block A",
            "metric": "energy",
            "badge": "Auto-Recommend",
            "badge_color": "green",
            "description": "Energy consumption +15% in June (38°C ambient). Operational sensor. Historic 12-month match.",
            "data": {
                "query": "Academic Block A energy consumption increased by 15% in June during 38°C heatwave",
                "metric_data": {
                    "current": 12500,
                    "baseline": 10870,
                    "type": "energy",
                    "month": "June",
                    "building": "Academic Block A",
                    "building_type": "Academic",
                    "context": {
                        "sensor_status": "operational",
                        "days_since_calibration": 45,
                        "ambient_temp": "38°C",
                        "events": "None unusual"
                    }
                }
            }
        },
        {
            "id": "scenario_b",
            "name": "Scenario B: Hostel Water Spike with New Sensor (Med Conf)",
            "building": "Hostel C",
            "metric": "water",
            "badge": "Warn + Monitor",
            "badge_color": "amber",
            "description": "Water usage +35% at 6 AM. Sensor replaced 2 days ago (burn-in period). Annual Day yesterday.",
            "data": {
                "query": "Water usage increased 35% in Hostel C. Sensor replaced 2 days ago. Annual day event yesterday.",
                "metric_data": {
                    "current": 15000,
                    "baseline": 11100,
                    "type": "water",
                    "month": "April",
                    "building": "Hostel C",
                    "building_type": "Residential",
                    "context": {
                        "sensor_status": "recently_replaced",
                        "days_since_calibration": 2,
                        "time": "06:00",
                        "events": "Annual Day celebration"
                    }
                }
            }
        },
        {
            "id": "scenario_c",
            "name": "Scenario C: 2:47 AM Critical Spike - Fire/Fault (Low Conf / Escalate)",
            "building": "Chemistry Lab",
            "metric": "energy",
            "badge": "HUMAN ESCALATION",
            "badge_color": "red",
            "description": "Energy +380% spike at 2:47 AM. Accelerating rate. High risk of electrical fire or breaker short.",
            "data": {
                "query": "Extreme overnight energy surge of 380% in Chemistry Lab at 2:47 AM. No scheduled activities.",
                "metric_data": {
                    "current": 28000,
                    "baseline": 5833,
                    "type": "energy",
                    "month": "March",
                    "building": "Chemistry Lab",
                    "building_type": "Laboratory",
                    "context": {
                        "sensor_status": "operational",
                        "time": "02:47",
                        "events": "None scheduled",
                        "rate_of_increase": "ACCELERATING"
                    }
                }
            }
        },
        {
            "id": "scenario_solar",
            "name": "Scenario D: Solar Microgrid Inverter Drop",
            "building": "Solar Farm Array 3",
            "metric": "energy",
            "badge": "Warn + Monitor",
            "badge_color": "amber",
            "description": "Midday generation drop of -45% with inverter telemetry communication timeout.",
            "data": {
                "query": "Solar array generation dropped 45% during peak noon irradiance",
                "metric_data": {
                    "current": 5500,
                    "baseline": 10000,
                    "type": "energy",
                    "month": "May",
                    "building": "Solar Farm Array 3",
                    "building_type": "Renewable",
                    "context": {
                        "sensor_status": "operational",
                        "days_since_calibration": 80
                    }
                }
            }
        }
    ]

@app.get("/api/alerts")
def get_alerts():
    """Parse alerts log file and return active human escalation queue."""
    alerts = []
    if not os.path.exists(ALERTS_LOG_PATH):
        return []

    try:
        with open(ALERTS_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        blocks = content.split("=" * 60)
        for b in blocks:
            b_clean = b.strip()
            if not b_clean:
                continue

            alert_id_m = re.search(r"Alert ID:\s*(ALERT-[A-Z0-9]+)", b_clean)
            building_m = re.search(r"Building:\s*(.+)", b_clean)
            issue_m = re.search(r"Issue:\s*(.+)", b_clean)
            detected_m = re.search(r"Detected:\s*(.+)", b_clean)
            confidence_m = re.search(r"System Confidence:\s*([0-9]+%)", b_clean)
            priority_m = re.search(r"Priority\s*-\s*([A-Z]+)", b_clean) or re.search(r"EcoOps Alert\s*-\s*([A-Z]+)\s*Priority", b_clean)

            if alert_id_m:
                aid = alert_id_m.group(1).strip()
                is_ack = aid in _acknowledged_alerts
                alerts.append({
                    "alert_id": aid,
                    "building": building_m.group(1).strip() if building_m else "Campus Facility",
                    "issue": issue_m.group(1).strip() if issue_m else "Operational Anomaly",
                    "detected": detected_m.group(1).strip() if detected_m else "Recent",
                    "confidence": confidence_m.group(1).strip() if confidence_m else "N/A",
                    "priority": priority_m.group(1).strip() if priority_m else "HIGH",
                    "status": "Acknowledged" if is_ack else "Pending Dispatch",
                    "ack_details": _acknowledged_alerts.get(aid, None),
                    "recipients": ["facilities@campus.edu", "security@campus.edu", "ehs-dispatch@campus.edu"],
                    "raw": b_clean
                })
        
        # Return latest alerts first
        alerts.reverse()
        return alerts
    except Exception as e:
        return [{"error": f"Failed reading alerts log: {e}"}]

@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, req: AcknowledgeRequest):
    """Acknowledge an escalation alert."""
    _acknowledged_alerts[alert_id] = {
        "acknowledged_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "officer": req.officer,
        "notes": req.notes,
        "status": "Dispatched Physical Team"
    }
    return {
        "status": "success",
        "alert_id": alert_id,
        "details": _acknowledged_alerts[alert_id]
    }

@app.get("/api/evaluate")
def run_evaluation_benchmark():
    """Trigger the 20-scenario benchmark evaluation and return detailed metrics."""
    results = evaluate_ecoops()
    return results

@app.get("/api/policies")
def list_policies():
    """Return all campus knowledge base policies and guides."""
    policies = []
    if os.path.exists(KB_DIR):
        for fname in os.listdir(KB_DIR):
            if fname.endswith(".md"):
                fpath = os.path.join(KB_DIR, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    text = f.read()
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                title = lines[0].replace("#", "").strip() if lines else fname
                policies.append({
                    "filename": fname,
                    "title": title,
                    "preview": text[:300] + "...",
                    "full_content": text
                })
    return policies

@app.post("/api/upload-csv")
async def upload_anomaly_csv(file: UploadFile = File(...)):
    """Process uploaded CSV of campus building anomalies."""
    try:
        content = await file.read()
        lines = content.decode("utf-8").strip().split("\n")
        if len(lines) < 2:
            raise HTTPException(status_code=400, detail="CSV file must have header and at least 1 data row.")

        header = [h.strip().lower() for h in lines[0].split(",")]
        batch_results = []

        for line in lines[1:25]:  # process up to 25 items
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            row = dict(zip(header, parts))
            
            # Map columns
            current_val = float(row.get("current", row.get("value", 10000)))
            baseline_val = float(row.get("baseline", 10000))
            metric_type = row.get("metric", row.get("type", "energy"))
            building = row.get("building", "Campus Facility")
            month = row.get("month", "June")
            
            req_data = {
                "query": f"Analyze {metric_type} consumption in {building}",
                "metric_data": {
                    "current": current_val,
                    "baseline": baseline_val,
                    "type": metric_type,
                    "month": month,
                    "building": building,
                    "context": {
                        "sensor_status": row.get("sensor_status", "operational"),
                        "days_since_calibration": int(row.get("days_since_calibration", 45))
                    }
                }
            }
            res = ecoops_app.invoke(req_data)
            batch_results.append({
                "building": building,
                "metric": metric_type,
                "current": current_val,
                "baseline": baseline_val,
                "percent_change": res.get("anomaly_result", {}).get("percent_change", 0.0),
                "confidence": res.get("overall_confidence", 0.0),
                "decision": res.get("decision_band", "unknown"),
                "should_escalate": res.get("should_escalate", False),
                "recommendation": res.get("recommendations", [{}])[0].get("title", "")
            })

        return {
            "status": "success",
            "processed_count": len(batch_results),
            "results": batch_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")

# Mount static files for dashboard frontend
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
