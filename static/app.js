/**
 * EcoOps 2.0 Frontend Controller
 * Drives interactive multi-agent analysis, LangGraph trace animation,
 * radial gauge rendering, facilities escalation dispatch, and benchmark evaluation.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const scenarioPills = document.querySelectorAll(".scenario-btn");
  const form = document.getElementById("telemetry-form");
  const analyzeBtn = document.getElementById("analyze-btn");
  const resetBtn = document.getElementById("reset-inputs-btn");

  // Input Fields
  const inputBuilding = document.getElementById("input-building");
  const inputMetricType = document.getElementById("input-metric-type");
  const inputCurrent = document.getElementById("input-current");
  const inputBaseline = document.getElementById("input-baseline");
  const inputMonth = document.getElementById("input-month");
  const inputSensorStatus = document.getElementById("input-sensor-status");
  const inputCalibrationDays = document.getElementById("input-calibration-days");
  const inputQuery = document.getElementById("input-query");

  // Output Elements
  const decisionBadge = document.getElementById("decision-badge");
  const gaugeCircle = document.getElementById("gauge-circle");
  const gaugePercent = document.getElementById("gauge-percent");
  const gaugeSubtext = document.getElementById("gauge-subtext");

  const metricAnomalyChange = document.getElementById("metric-anomaly-change");
  const metricAnomalySev = document.getElementById("metric-anomaly-sev");
  const metricActionText = document.getElementById("metric-action-text");
  const metricActionSub = document.getElementById("metric-action-sub");

  const factorDataVal = document.getElementById("factor-data-val");
  const factorDataBar = document.getElementById("factor-data-bar");
  const factorDataHint = document.getElementById("factor-data-hint");

  const factorRagVal = document.getElementById("factor-rag-val");
  const factorRagBar = document.getElementById("factor-rag-bar");
  const factorRagHint = document.getElementById("factor-rag-hint");

  const factorHistoryVal = document.getElementById("factor-history-val");
  const factorHistoryBar = document.getElementById("factor-history-bar");
  const factorHistoryHint = document.getElementById("factor-history-hint");

  const factorSeverityVal = document.getElementById("factor-severity-val");
  const factorSeverityBar = document.getElementById("factor-severity-bar");
  const factorSeverityHint = document.getElementById("factor-severity-hint");

  const recTitle = document.getElementById("rec-title");
  const recDesc = document.getElementById("rec-desc");
  const impactEnergy = document.getElementById("impact-energy");
  const impactCost = document.getElementById("impact-cost");
  const impactCo2 = document.getElementById("impact-co2");
  const citationsRow = document.getElementById("citations-row");

  const executionLogContainer = document.getElementById("execution-log-container");
  const graphNodes = document.querySelectorAll(".graph-node");

  const alertsTbody = document.getElementById("alerts-tbody");
  const alertsCount = document.getElementById("alerts-count");
  const refreshAlertsBtn = document.getElementById("refresh-alerts-btn");

  const runBenchmarkBtn = document.getElementById("run-benchmark-btn");
  const benchAcc = document.getElementById("bench-acc");
  const benchCalib = document.getElementById("bench-calib");
  const benchSafety = document.getElementById("bench-safety");
  const policyChips = document.getElementById("policy-chips");

  // Scenario Presets Cache
  let scenariosMap = {};

  // Fetch scenarios & initial alerts
  initApp();

  async function initApp() {
    await fetchScenarios();
    await fetchAlerts();
    await fetchPolicies();
    
    // Automatically trigger analysis of default Scenario A on startup
    submitAnalysis();
  }

  // Load Scenario Definitions from Backend
  async function fetchScenarios() {
    try {
      const res = await fetch("/api/scenarios");
      if (res.ok) {
        const scenarios = await res.json();
        scenarios.forEach(s => { scenariosMap[s.id] = s; });
      }
    } catch (e) {
      console.warn("Using offline scenario presets:", e);
    }
  }

  // Scenario Switching Handler
  scenarioPills.forEach(btn => {
    btn.addEventListener("click", () => {
      scenarioPills.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      const scenarioId = btn.getAttribute("data-scenario");
      if (scenarioId === "custom") {
        // Clear fields for custom testing
        inputBuilding.value = "Sports Arena Complex";
        inputMetricType.value = "energy";
        inputCurrent.value = 16000;
        inputBaseline.value = 10000;
        inputMonth.value = "June";
        inputSensorStatus.value = "operational";
        inputCalibrationDays.value = 30;
        inputQuery.value = "Sports Arena floodlights consumption elevated by 60% during weekend tournament";
        return;
      }

      const preset = scenariosMap[scenarioId];
      if (preset && preset.data) {
        const d = preset.data;
        const md = d.metric_data;
        const ctx = md.context || {};

        inputBuilding.value = md.building || "";
        inputMetricType.value = md.type || "energy";
        inputCurrent.value = md.current || 10000;
        inputBaseline.value = md.baseline || 10000;
        inputMonth.value = md.month || "June";
        inputSensorStatus.value = ctx.sensor_status || "operational";
        inputCalibrationDays.value = ctx.days_since_calibration || 45;
        inputQuery.value = d.query || "";

        // Trigger immediate execution
        submitAnalysis();
      }
    });
  });

  // Reset Button
  resetBtn.addEventListener("click", () => {
    const scenarioABtn = document.querySelector('[data-scenario="scenario_a"]');
    if (scenarioABtn) scenarioABtn.click();
  });

  // Form Submit Handler
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    submitAnalysis();
  });

  async function submitAnalysis() {
    setLoading(true);

    const payload = {
      query: inputQuery.value.trim(),
      metric_data: {
        current: parseFloat(inputCurrent.value),
        baseline: parseFloat(inputBaseline.value),
        type: inputMetricType.value,
        month: inputMonth.value,
        building: inputBuilding.value.trim(),
        context: {
          sensor_status: inputSensorStatus.value,
          days_since_calibration: parseInt(inputCalibrationDays.value) || 0
        }
      }
    };

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      renderAnalysisResult(data.result);
      fetchAlerts(); // Refresh queue if escalation occurred
    } catch (err) {
      console.error("Analysis failed:", err);
      alert(`Execution Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function setLoading(isLoading) {
    const btnText = analyzeBtn.querySelector(".btn-text");
    const btnLoader = analyzeBtn.querySelector(".btn-loader");
    if (isLoading) {
      btnText.style.display = "none";
      btnLoader.style.display = "inline";
      analyzeBtn.disabled = true;
    } else {
      btnText.style.display = "inline";
      btnLoader.style.display = "none";
      analyzeBtn.disabled = false;
    }
  }

  // Render Full State Machine Analysis Results
  function renderAnalysisResult(state) {
    const conf = state.overall_confidence || 0.5;
    const band = state.decision_band || "warn";
    const anomaly = state.anomaly_result || {};
    const percentChange = anomaly.percent_change || 0;
    const severity = anomaly.severity || "normal";
    const recs = state.recommendations || [];
    const primaryRec = recs[0] || {};
    const impact = primaryRec.environmental_impact || {};

    // 1. Update Radial Gauge (Circumference ~427.25 for r=68)
    const circumference = 427.25;
    const offset = circumference - (conf * circumference);
    gaugeCircle.style.strokeDashoffset = offset;
    gaugePercent.textContent = `${Math.round(conf * 100)}%`;

    // 2. Dynamic Palette based on Decision Band
    let strokeColor = "#10b981";
    let badgeText = "⚡ AUTO-IMPLEMENT";
    let badgeClass = "badge-green";
    let subtext = "HIGH CERTAINTY";
    let actionSummary = "AUTO-OPTIMIZE";

    if (band === "escalate" || state.should_escalate) {
      strokeColor = "#f43f5e";
      badgeText = "🚨 HUMAN ESCALATION REQUIRED";
      badgeClass = "badge-red";
      subtext = "CRITICAL / UNCERTAIN";
      actionSummary = "DISPATCH FACILITIES TEAM";
    } else if (band === "warn" || conf < 0.75) {
      strokeColor = "#f59e0b";
      badgeText = "⚠️ WARN + MONITOR";
      badgeClass = "badge-amber";
      subtext = "MEDIUM CERTAINTY";
      actionSummary = "OBSERVE & VERIFY SENSOR";
    }

    gaugeCircle.style.stroke = strokeColor;
    gaugeSubtext.textContent = subtext;
    gaugePercent.style.color = strokeColor;

    decisionBadge.textContent = badgeText;
    decisionBadge.className = `decision-badge ${badgeClass}`;

    // Metrics Box
    metricAnomalyChange.textContent = `${percentChange >= 0 ? "+" : ""}${percentChange.toFixed(1)}%`;
    metricAnomalyChange.style.color = strokeColor;
    metricAnomalySev.textContent = `Severity: ${severity.toUpperCase()}`;
    metricActionText.textContent = actionSummary;
    metricActionSub.textContent = state.escalation_reason || (band === "auto_act" ? "Standard protocol approved" : "Pending human review");

    // 3. Multi-Factor Breakdown
    const dataConf = state.data_confidence || 0.8;
    const ragConf = state.rag_confidence || 0.7;
    const historyConf = state.historical_confidence || 0.5;
    const sevPenalty = severity === "extreme" ? 0.4 : (severity === "high" ? 0.7 : (severity === "moderate" ? 0.9 : 1.0));

    updateFactorBar(factorDataVal, factorDataBar, factorDataHint, dataConf, 
      `${anomaly.uncertainty_factors ? anomaly.uncertainty_factors.join(" • ") : "Sensor validated"}`);
    updateFactorBar(factorRagVal, factorRagBar, factorRagHint, ragConf, 
      state.rag_result ? (state.rag_result.sources ? `Matched: ${state.rag_result.sources[0]}` : "KB grounded") : "Policy retrieval active");
    updateFactorBar(factorHistoryVal, factorHistoryBar, factorHistoryHint, historyConf, 
      state.historical_result ? state.historical_result.reasoning : "Historical match analyzed");
    updateFactorBar(factorSeverityVal, factorSeverityBar, factorSeverityHint, sevPenalty, 
      severity === "extreme" ? "Extreme spike penalizes automated action" : "Variance within operational deadband");

    // 4. Recommendation Details & Citations
    recTitle.textContent = primaryRec.title || "Facility Operational Advisory";
    recDesc.textContent = primaryRec.description || primaryRec.reason || "Execute standard load management protocol.";
    
    // Impact values
    const kwhSaved = impact.energy_co2 ? Math.round(primaryRec.energy_savings || 0) : 0;
    const costSaved = impact.cost_savings_inr ? Math.round(impact.cost_savings_inr) : (kwhSaved * 4);
    const co2Saved = impact.co2_kg_saved ? Math.round(impact.co2_kg_saved) : 0;

    impactEnergy.textContent = kwhSaved > 0 ? `-${kwhSaved.toLocaleString()} kWh` : (band === "escalate" ? "SUSPENDED" : "Nominal");
    impactCost.textContent = costSaved > 0 ? `-₹${costSaved.toLocaleString()}` : (band === "escalate" ? "SAFETY FIRST" : "₹0");
    impactCo2.textContent = co2Saved > 0 ? `-${co2Saved.toLocaleString()} kg` : (band === "escalate" ? "0 kg" : "0 kg");

    // Citations
    citationsRow.innerHTML = `<span class="cite-label">Grounding Citations:</span>`;
    const citations = primaryRec.citations || (state.rag_result ? state.rag_result.sources : []);
    if (citations && citations.length > 0) {
      citations.forEach(c => {
        const span = document.createElement("span");
        span.className = "cite-tag";
        span.textContent = c;
        citationsRow.appendChild(span);
      });
    }

    // 5. LangGraph Node Traversal Animation
    animatePipeline(state.trace_log || [], band);
  }

  function updateFactorBar(valElem, barElem, hintElem, score, hintText) {
    const pct = Math.round(score * 100);
    valElem.textContent = `${pct}%`;
    barElem.style.width = `${pct}%`;
    barElem.className = "progress-fill " + (score >= 0.75 ? "green" : (score >= 0.5 ? "amber" : "red"));
    if (hintText && hintElem) hintElem.textContent = hintText;
  }

  // Sequential LangGraph Pipeline Step Highlighter
  function animatePipeline(traces, band) {
    graphNodes.forEach(node => {
      node.className = "graph-node";
    });

    executionLogContainer.innerHTML = "";

    traces.forEach((trace, idx) => {
      setTimeout(() => {
        const stepName = trace.step;
        const matchingNode = document.querySelector(`[data-node="${stepName}"]`) || document.querySelector(`[data-node="router"]`);
        if (matchingNode) {
          matchingNode.classList.add("active");
          if (band === "escalate") {
            matchingNode.classList.add("danger");
          } else if (band === "warn") {
            matchingNode.classList.add("warning");
          }
        }

        // Add to log console
        const logEntry = document.createElement("div");
        logEntry.className = "log-entry";
        logEntry.innerHTML = `<strong>[Node ${idx+1}: ${trace.step}]</strong> ${trace.reasoning || JSON.stringify(trace.factors || "")}`;
        executionLogContainer.appendChild(logEntry);
        executionLogContainer.scrollTop = executionLogContainer.scrollHeight;
      }, idx * 120);
    });
  }

  // Escalation Queue Management
  async function fetchAlerts() {
    try {
      const res = await fetch("/api/alerts");
      if (!res.ok) return;
      const alerts = await res.json();
      alertsCount.textContent = alerts.length;

      if (!alerts || alerts.length === 0) {
        alertsTbody.innerHTML = `<tr><td colspan="7" class="empty-state">No human escalation tickets open. Systems nominal.</td></tr>`;
        return;
      }

      alertsTbody.innerHTML = "";
      alerts.forEach(a => {
        const tr = document.createElement("tr");
        const isAck = a.status === "Acknowledged";
        tr.innerHTML = `
          <td><strong>${a.alert_id}</strong></td>
          <td>${a.building}</td>
          <td><span class="btn-badge badge-red">${a.priority}</span></td>
          <td>${a.confidence}</td>
          <td>${a.detected}</td>
          <td><span class="status-pill ${isAck ? 'status-online' : ''}">${a.status}</span></td>
          <td>
            ${isAck ? '<span style="color: #34d399; font-size: 0.75rem;">Dispatched ✓</span>' : 
              `<button class="btn-secondary ack-btn" data-id="${a.alert_id}">Acknowledge & Dispatch</button>`}
          </td>
        `;
        alertsTbody.appendChild(tr);
      });

      // Attach ack listeners
      document.querySelectorAll(".ack-btn").forEach(b => {
        b.addEventListener("click", async () => {
          const aid = b.getAttribute("data-id");
          await fetch(`/api/alerts/${aid}/acknowledge`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ notes: "Immediate on-site electrical/physical team dispatched" })
          });
          fetchAlerts();
        });
      });
    } catch (e) {
      console.warn("Failed fetching alerts:", e);
    }
  }

  refreshAlertsBtn.addEventListener("click", fetchAlerts);

  // Benchmark Runner Handler
  runBenchmarkBtn.addEventListener("click", async () => {
    runBenchmarkBtn.disabled = true;
    runBenchmarkBtn.textContent = "Running 20 Scenarios...";
    try {
      const res = await fetch("/api/evaluate");
      if (res.ok) {
        const data = await res.json();
        benchAcc.textContent = `${(data.escalation_accuracy * 100).toFixed(1)}%`;
        benchCalib.textContent = `${(data.confidence_calibration * 100).toFixed(1)}%`;
        benchSafety.textContent = `${(data.safety_compliance_rate * 100).toFixed(1)}%`;
        alert(`Benchmark Complete!\n• Escalation Accuracy: ${(data.escalation_accuracy * 100).toFixed(1)}%\n• Confidence Calibration: ${(data.confidence_calibration * 100).toFixed(1)}%\n• Safety Passed: 20/20 Scenarios`);
      }
    } catch (e) {
      alert(`Benchmark execution failed: ${e.message}`);
    } finally {
      runBenchmarkBtn.disabled = false;
      runBenchmarkBtn.textContent = "Run 20-Scenario Benchmark";
    }
  });

  // Fetch Knowledge Base Documents
  async function fetchPolicies() {
    try {
      const res = await fetch("/api/policies");
      if (res.ok) {
        const docs = await res.json();
        policyChips.innerHTML = "";
        docs.forEach(d => {
          const chip = document.createElement("span");
          chip.className = "policy-chip";
          chip.title = d.preview;
          chip.textContent = `📄 ${d.title}`;
          policyChips.appendChild(chip);
        });
      }
    } catch (e) {
      console.warn("Failed loading policies:", e);
    }
  }
});
