import json
import textwrap
import pandas as pd
from pathlib import Path
from anomaly import detect_anomalies

# Official ArduPilot MAVLink Log Messages Documentation (Condensed for Flight Analysis)
ARDUPILOT_DOCS = """
OFFICIAL ARDUPILOT MAVLINK LOG MESSAGES REFERENCE:

== CRITICAL FLIGHT DATA MESSAGES ==

ATT (Canonical vehicle attitude):
- DesRoll/Roll: desired vs achieved roll (deg)
- DesPitch/Pitch: desired vs achieved pitch (deg) 
- DesYaw/Yaw: desired vs achieved heading (degheading)
- AEKF: active EKF type

GPS (Global positioning data):
- Status: 0=no GPS, 1=no fix, 2=2D fix, 3=3D fix
- Time: GPS time since epoch (milliseconds)
- NSats: number of satellites in use
- HDop: horizontal dilution of precision (<1.5=excellent, <2.0=good, >3.0=poor)
- Lat/Lng: position coordinates (deg)
- Alt: GPS altitude (m) - NOT used by autopilot for navigation
- RelAlt: accelerometer + barometer altitude (m)
- SPD: horizontal ground speed (m/s)
- GCrs: ground course (degrees, 0=north)

BARO (Barometer data):
- Alt: calculated altitude above sea level (m)
- Press: atmospheric pressure (Pa)
- Temp: atmospheric temperature (degC)
- CRt: climb rate from barometer (m/s)
- H: true if barometer healthy

BAT (Battery data):
- Volt: measured voltage (V)
- VoltR: estimated resting voltage (V)
- Curr: measured current (A)
- CurrTot: total consumed current (mAh)
- EnrgTot: total energy consumed (Wh)
- Temp: battery temperature (degC)
- RemPct: remaining percentage (%)
- H: health status

IMU/ACC (Inertial measurement):
- AccX/Y/Z: acceleration along each axis (m/s/s)
- GyrX/Y/Z: gyroscope rates (rad/s or deg/s)

== CONTROL AND NAVIGATION ==

CTUN (Control tuning - varies by vehicle):
[Plane] NavRoll/Roll: desired vs achieved roll
[Plane] NavPitch/Pitch: desired vs achieved pitch  
[Plane] ThO: scaled throttle output
[Plane] As: airspeed estimate (m/s)
[Copter] ThI: throttle input, ThO: throttle output
[Copter] DAlt/Alt: desired vs achieved altitude (m)
[Copter] DCRt/CRt: desired vs achieved climb rate (cm/s)

MODE (Flight mode changes):
- Mode: flight mode as string (STABILIZE, AUTO, RTL, etc.)
- ThrCrs: throttle cruise estimate
- Rsn: reason for mode change

NTUN (Navigation tuning - Copter):
- WPDst: distance to waypoint (cm)
- WPBrg: bearing to waypoint (deg)
- PErX/Y: position error (cm)
- DVelX/Y: desired velocity (cm/s)
- VelX/Y: actual velocity estimate (cm/s)

== ERROR AND EVENT MESSAGES ==

ERR (Error messages):
Subsystem codes:
- 2=Radio, 3=Compass, 5=Radio Failsafe, 6=Battery Failsafe
- 8=GCS Failsafe, 9=Fence Failsafe, 10=Flight Mode Change
- 11=GPS, 12=Crash Check, 15=Parachute, 16=EKF Check
- 17=EKF Failsafe, 18=Barometer, 21=Terrain Data

ARM (Arming status):
- ArmState: true if armed
- ArmChecks: bitmask of arming checks
- Method: arming method (RUDDER, MAVLINK, etc.)

EVENT (EV):
- 10=Armed, 11=Disarmed, 15=Auto Armed
- 18=Land Complete, 25=Set Home, 28=Takeoff Complete

== SENSOR QUALITY INDICATORS ==

ARSP (Airspeed sensor):
- Airspeed: current airspeed (m/s)
- DiffPress: pressure differential (Pa)
- U: true if being used
- H: true if healthy

GPA (GPS accuracy):
- VDop: vertical dilution of precision
- HAcc: horizontal accuracy (m)
- VAcc: vertical accuracy (m)
- SAcc: speed accuracy (m/s/s)

== ANALYSIS GUIDELINES ==

NORMAL VALUES:
- GPS HDop: <2.0 for good fix, <1.5 for excellent
- GPS satellites: 6+ required for 3D fix
- Battery voltage: 3S LiPo = 11.1V-12.6V nominal
- Barometer: should track GPS altitude reasonably
- Attitude: Roll/Pitch within ±45° for normal flight

ANOMALY INDICATORS:
- GPS: HDop >3.0, NSats <6, large position jumps
- Battery: voltage <11.5V (3S), sudden drops >0.5V
- Altitude: sudden changes >20m, negative altitude
- Attitude: extreme angles >45°, rapid changes >30°/sample
- Errors: Any ERR messages indicate system problems
- Mode changes: Unexpected mode changes may indicate failsafes

FLIGHT PHASES:
- Pre-arm: System checks, GPS acquisition
- Takeoff: Initial altitude gain, mode transitions
- Cruise: Normal flight operations, waypoint navigation
- Landing: Controlled descent, mode changes to LAND/RTL
- Emergency: Failsafe activations, error conditions

TIME REFERENCES:
- TimeUS: microseconds since system startup
- All analysis should consider temporal relationships
- Look for patterns over time, not just instantaneous values
"""

# If you later download/paste additional ArduPilot docs, put them in backend/mav_docs.md.
_DOC_PATH = Path(__file__).with_name("mav_docs.md")
DOC_TEXT = _DOC_PATH.read_text() if _DOC_PATH.exists() else ARDUPILOT_DOCS


def create_agentic_reasoning_context(df: pd.DataFrame) -> dict:
    """Create dynamic analysis context that encourages flexible reasoning."""
    
    # Generate data patterns for AI to analyze
    data_insights = {
        "temporal_patterns": {},
        "value_distributions": {},
        "correlation_hints": {},
        "anomaly_indicators": {}
    }
    
    # Temporal pattern analysis
    if "TimeUS" in df.columns:
        duration = float(df["TimeUS"].max() - df["TimeUS"].min()) / 1e6
        data_insights["temporal_patterns"]["flight_duration_sec"] = duration
        data_insights["temporal_patterns"]["sample_rate"] = len(df) / duration if duration > 0 else 0
        data_insights["temporal_patterns"]["data_density"] = "high" if len(df) > 1000 else "medium" if len(df) > 100 else "low"
    
    # Value distribution analysis
    for col in ["Alt", "Volt", "HDop", "NSats", "Roll", "Pitch", "Yaw"]:
        if col in df.columns:
            values = df[col].dropna()
            if len(values) > 0:
                data_insights["value_distributions"][col] = {
                    "range": float(values.max() - values.min()),
                    "variance": float(values.var()),
                    "trend": "increasing" if values.iloc[-1] > values.iloc[0] else "decreasing",
                    "stability": "stable" if values.std() < values.mean() * 0.1 else "variable"
                }
    
    # Correlation hints (encourage AI to find relationships)
    correlation_suggestions = []
    if "Alt" in df.columns and "Volt" in df.columns:
        correlation_suggestions.append("altitude_vs_battery_consumption_analysis")
    if "HDop" in df.columns and "NSats" in df.columns:
        correlation_suggestions.append("gps_precision_vs_satellite_count_correlation")
    if "Roll" in df.columns and "Pitch" in df.columns:
        correlation_suggestions.append("attitude_stability_and_control_analysis")
    if "ThI" in df.columns and "ThO" in df.columns:
        correlation_suggestions.append("throttle_input_vs_output_response_analysis")
    
    data_insights["correlation_hints"]["suggested_analyses"] = correlation_suggestions
    
    # Anomaly indicators (suggestions, not rules)
    anomaly_suggestions = []
    for col in df.columns:
        if col in ["Alt", "Volt", "HDop", "Roll", "Pitch", "Yaw", "NSats"]:
            values = df[col].dropna()
            if len(values) > 1:
                rate_of_change = values.diff().abs().max()
                if rate_of_change > values.std() * 3:  # Suggest looking at high variance
                    anomaly_suggestions.append(f"investigate_rapid_changes_in_{col}_over_time")
    
    data_insights["anomaly_indicators"]["investigation_suggestions"] = anomaly_suggestions
    
    return data_insights


def generate_investigative_prompts(df: pd.DataFrame) -> list:
    """Generate context-specific investigative questions for the AI to consider."""
    
    prompts = []
    
    # GPS investigation prompts
    if "HDop" in df.columns:
        avg_hdop = df["HDop"].mean()
        max_hdop = df["HDop"].max()
        if avg_hdop > 2.0:
            prompts.append(f"GPS precision is concerning (avg HDop: {avg_hdop:.1f}, max: {max_hdop:.1f}). Investigate what flight conditions correlate with GPS degradation.")
    
    if "NSats" in df.columns:
        min_sats = df["NSats"].min()
        if min_sats < 6:
            prompts.append(f"Satellite count dropped to {min_sats}. Analyze when this occurred and its impact on navigation accuracy.")
    
    # Battery analysis prompts
    if "Volt" in df.columns:
        min_voltage = df["Volt"].min()
        max_voltage = df["Volt"].max()
        voltage_drop = max_voltage - min_voltage
        if voltage_drop > 0.5:
            prompts.append(f"Significant battery discharge detected ({voltage_drop:.1f}V drop from {max_voltage:.1f}V to {min_voltage:.1f}V). Correlate power consumption with flight maneuvers.")
    
    # Altitude behavior prompts
    if "Alt" in df.columns:
        alt_variance = df["Alt"].var()
        alt_range = df["Alt"].max() - df["Alt"].min()
        if alt_variance > 100:
            prompts.append(f"High altitude variability detected (range: {alt_range:.1f}m). Distinguish between intentional maneuvers and potential control issues.")
    
    # Control system prompts
    attitude_cols = ["Roll", "Pitch", "Yaw"]
    available_attitude = [col for col in attitude_cols if col in df.columns]
    if available_attitude:
        for col in available_attitude:
            max_angle = abs(df[col]).max() if col in df.columns else 0
            if max_angle > 30:
                prompts.append(f"Extreme {col.lower()} attitude detected ({max_angle:.1f}°). Analyze if this represents aggressive maneuvering or control instability.")
    
    # Flight mode analysis
    if "Mode" in df.columns:
        mode_changes = len(df["Mode"].unique()) if "Mode" in df.columns else 0
        if mode_changes > 3:
            prompts.append(f"Multiple flight mode changes detected ({mode_changes} different modes). Investigate reasons for mode transitions.")
    
    return prompts


def build_prompt(df: pd.DataFrame, chat_history):
    """Return a system prompt dict for OpenAI ChatCompletion with enhanced agentic reasoning."""
    
    # Enhanced flight summary with contextual analysis
    duration_sec = float(df["TimeUS"].max() / 1e6) if "TimeUS" in df else None
    max_altitude = float(df["Alt"].max()) if "Alt" in df else None
    min_altitude = float(df["Alt"].min()) if "Alt" in df else None
    
    # GPS quality analysis with official thresholds
    gps_quality = "Unknown"
    gps_context = ""
    if "HDop" in df:
        avg_hdop = df["HDop"].mean()
        max_hdop = df["HDop"].max()
        min_hdop = df["HDop"].min()
        if avg_hdop < 1.5:
            gps_quality = "Excellent"
            gps_context = f"consistently excellent precision (avg HDop: {avg_hdop:.1f})"
        elif avg_hdop < 2.0:
            gps_quality = "Good" 
            gps_context = f"good precision with minor variations (avg HDop: {avg_hdop:.1f}, max: {max_hdop:.1f})"
        elif avg_hdop < 3.0:
            gps_quality = "Fair"
            gps_context = f"variable precision requiring investigation (avg HDop: {avg_hdop:.1f}, range: {min_hdop:.1f}-{max_hdop:.1f})"
        else:
            gps_quality = "Poor"
            gps_context = f"degraded precision indicating interference or poor satellite geometry (avg HDop: {avg_hdop:.1f}, max: {max_hdop:.1f})"
    
    # Enhanced battery analysis
    battery_health = "Unknown"
    battery_context = ""
    if "Volt" in df:
        min_voltage = df["Volt"].min()
        max_voltage = df["Volt"].max()
        avg_voltage = df["Volt"].mean()
        voltage_drop = max_voltage - min_voltage
        
        if min_voltage > 12.0:
            battery_health = "Excellent"
            battery_context = f"healthy voltage throughout flight ({min_voltage:.1f}V-{max_voltage:.1f}V, drop: {voltage_drop:.1f}V)"
        elif min_voltage > 11.5:
            battery_health = "Good"
            battery_context = f"adequate voltage with moderate consumption (min: {min_voltage:.1f}V, avg: {avg_voltage:.1f}V, total drop: {voltage_drop:.1f}V)"
        elif min_voltage > 11.1:
            battery_health = "Fair"
            battery_context = f"approaching minimum safe voltage (min: {min_voltage:.1f}V indicates high consumption or battery aging)"
        else:
            battery_health = "Critical"
            battery_context = f"critically low voltage reached ({min_voltage:.1f}V), indicating excessive consumption or battery failure"
    
    # Create dynamic reasoning context
    reasoning_context = create_agentic_reasoning_context(df)
    investigative_prompts = generate_investigative_prompts(df)
    
    # Get structured anomaly analysis
    anomaly_analysis = detect_anomalies(df)
    
    summary = {
        "flight_duration_sec": duration_sec,
        "flight_duration_min": round(duration_sec / 60, 1) if duration_sec else None,
        "max_altitude_m": max_altitude,
        "min_altitude_m": min_altitude,
        "altitude_range_m": max_altitude - min_altitude if max_altitude and min_altitude else None,
        "gps_quality": gps_quality,
        "gps_context": gps_context,
        "battery_health": battery_health,
        "battery_context": battery_context,
        "total_data_points": len(df),
        "available_sensors": list(df.columns),
        "data_quality": "high" if len(df) > 1000 else "medium" if len(df) > 100 else "basic"
    }

    return {
        "role": "system",
        "content": textwrap.dedent(
            f"""
            You are an expert UAV flight data analyst with deep knowledge of ArduPilot systems and MAVLink telemetry. 
            You excel at dynamic pattern recognition, contextual reasoning, and investigative analysis rather than rigid rule-based evaluation.

            CURRENT FLIGHT DATA SUMMARY:
            {json.dumps(summary, indent=2)}

            DYNAMIC REASONING CONTEXT:
            {json.dumps(reasoning_context, indent=2)}

            STRUCTURED ANOMALY ANALYSIS:
            {json.dumps(anomaly_analysis, indent=2)}

            INVESTIGATIVE FOCUS AREAS:
            {json.dumps(investigative_prompts, indent=2)}

            OFFICIAL ARDUPILOT MAVLINK DOCUMENTATION:
            {DOC_TEXT}

            AGENTIC BEHAVIOR GUIDELINES:
            
            1. **Maintain Conversation State**: Remember previous questions and build on prior analysis. Reference earlier findings when relevant.

            2. **Proactive Clarification**: Ask intelligent follow-up questions that demonstrate domain expertise:
               - "I detected GPS precision issues coinciding with altitude changes. Would you like me to investigate potential multipath interference patterns?"
               - "The battery shows non-linear discharge behavior. Should I analyze the correlation between power consumption and specific flight maneuvers?"
               - "I notice attitude variations that could indicate either pilot inputs or control system responses. Would you like me to examine the timing patterns and control authority?"

            3. **Dynamic Pattern Recognition**: Instead of applying fixed thresholds, analyze patterns in context of:
               - Flight phase (pre-arm, takeoff, cruise, landing, emergency)
               - Environmental conditions (GPS satellite geometry, interference)
               - Pilot intentions (aggressive maneuvering vs normal flight)
               - System limitations (battery capacity, control authority)

            4. **Investigative Reasoning**: When asked about anomalies, provide comprehensive analysis:
               - Root cause investigation using temporal correlations
               - System interdependency analysis (GPS↔battery, attitude↔control)
               - Flight safety implications with specific recommendations
               - Confidence levels when data is ambiguous

            5. **Contextual Thresholds**: Adapt analysis based on vehicle type and flight conditions:
               - Consider normal operating ranges for different flight phases
               - Account for vehicle-specific characteristics (plane vs copter)
               - Evaluate sensor accuracy and reliability contextually

            6. **Retrieve Telemetry Dynamically**: Access and cross-reference multiple data streams:
               - Correlate GPS quality with navigation performance
               - Link battery discharge to power demand patterns
               - Connect attitude changes to control inputs and outputs

            RESPONSE STYLE:
            - **Lead with insights**: Start with the most significant findings
            - **Provide evidence**: Quote specific values, timestamps, and data ranges
            - **Explain implications**: Clarify what findings mean for flight safety and performance
            - **Suggest investigations**: Recommend follow-up analyses when patterns need deeper exploration
            - **Ask clarifying questions**: When user intent is unclear, ask specific technical questions

            EXAMPLE INVESTIGATION APPROACH:
            Instead of: "Battery voltage dropped to 11.4V"
            Provide: "The battery exhibited concerning discharge characteristics, dropping from 12.3V to 11.4V over the final 2 minutes of flight (timestamps 180-300s). This 0.9V drop coincides with sustained high-power maneuvers between 250-280s, where GPS data shows rapid altitude changes from 45m to 75m. The discharge rate suggests either aggressive power demand or potential battery degradation. The timing correlation with GPS precision loss (HDop increased from 1.8 to 3.2) indicates possible electrical interference affecting multiple systems. Would you like me to analyze the power consumption patterns during specific maneuvers to determine if this is normal operational demand or indicates a system issue?"

            Always approach each query as a flight safety investigation, using your expertise to uncover the complete story behind the data.
            """
        ).strip(),
    }
