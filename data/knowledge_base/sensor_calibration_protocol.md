# Sensor Calibration Protocol & Telemetry Integrity Protocol (v2.1)
**Scope**: Ultrasonic Flow Meters, Smart Sub-Meters, IoT Telemetry Gateways  
**Authority**: Campus Instrumentation & Controls Department

---

## 1. Post-Replacement Burn-In Period (72 Hours)
When a smart utility meter (water flow meter, energy CT sensor, gas turbine meter) is replaced, serviced, or firmware-updated:
- **Telemetry Uncertainty**: Sensor output carries high variance during the initial 48 to 72 hours of operation.
- **Calibration Burn-In**: Flow coefficient $K$-factor and zero-point calibration require 48 hours of laminar flow to reach steady-state accuracy.
- **Policy Rule**: Anomalies reported by newly replaced sensors (< 3 days old) must NEVER trigger autonomous valve closures or HVAC load shedding.
- **Protocol Action**: Mark confidence as MEDIUM (0.50 - 0.70). Notify maintenance administrator, log observation window for 6 to 12 hours, and flag sensor calibration verification before dispatching emergency teams.

## 2. Sensor Drift and Maintenance Degradation
- Sensors with `days_since_calibration` > 180 days must apply an uncertainty penalty of 15% to reported readings.
- Sensors flagged with intermittent disconnects or packet drop > 5% require manual technician validation.
