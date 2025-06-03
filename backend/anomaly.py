import pandas as pd
import numpy as np


def detect_anomalies(df: pd.DataFrame) -> dict:
    """
    Comprehensive flight anomaly detection for UAV telemetry data.
    Returns a structured analysis of potential flight issues.
    """
    anomalies = {
        "summary": {"total_anomalies": 0, "severity": "normal"},
        "altitude_issues": [],
        "gps_problems": [],
        "battery_concerns": [],
        "control_anomalies": [],
        "navigation_issues": [],
        "system_errors": []
    }
    
    if len(df) < 2:
        return anomalies
    
    # 1. ALTITUDE ANOMALY DETECTION
    if "Alt" in df.columns:
        altitude_analysis = analyze_altitude_anomalies(df)
        anomalies["altitude_issues"] = altitude_analysis
        anomalies["summary"]["total_anomalies"] += len(altitude_analysis)
    
    # 2. GPS QUALITY ANALYSIS  
    if any(col in df.columns for col in ["HDop", "NSats", "Lat", "Lng"]):
        gps_analysis = analyze_gps_anomalies(df)
        anomalies["gps_problems"] = gps_analysis
        anomalies["summary"]["total_anomalies"] += len(gps_analysis)
    
    # 3. BATTERY/POWER SYSTEM ANALYSIS
    if any(col in df.columns for col in ["Volt", "Curr", "CurrTot"]):
        battery_analysis = analyze_battery_anomalies(df)
        anomalies["battery_concerns"] = battery_analysis
        anomalies["summary"]["total_anomalies"] += len(battery_analysis)
    
    # 4. CONTROL SYSTEM ANALYSIS
    if any(col in df.columns for col in ["Roll", "Pitch", "Yaw", "DesRoll", "DesPitch"]):
        control_analysis = analyze_control_anomalies(df)
        anomalies["control_anomalies"] = control_analysis
        anomalies["summary"]["total_anomalies"] += len(control_analysis)
    
    # 5. NAVIGATION ANALYSIS
    if any(col in df.columns for col in ["WPDst", "CRt", "VelX", "VelY"]):
        nav_analysis = analyze_navigation_anomalies(df)
        anomalies["navigation_issues"] = nav_analysis
        anomalies["summary"]["total_anomalies"] += len(nav_analysis)
    
    # 6. SYSTEM ERROR DETECTION
    if "msg_type" in df.columns:
        error_analysis = analyze_system_errors(df)
        anomalies["system_errors"] = error_analysis
        anomalies["summary"]["total_anomalies"] += len(error_analysis)
    
    # Determine overall severity
    total = anomalies["summary"]["total_anomalies"]
    if total == 0:
        anomalies["summary"]["severity"] = "normal"
    elif total <= 2:
        anomalies["summary"]["severity"] = "minor"
    elif total <= 5:
        anomalies["summary"]["severity"] = "moderate"
    else:
        anomalies["summary"]["severity"] = "critical"
    
    return anomalies


def analyze_altitude_anomalies(df: pd.DataFrame) -> list:
    """Detect altitude-related anomalies."""
    issues = []
    
    if "Alt" not in df.columns:
        return issues
    
    alt = df["Alt"].dropna()
    if len(alt) < 2:
        return issues
    
    # Large altitude changes (>20m in one sample)
    alt_diff = alt.diff().abs()
    large_changes = alt_diff > 20
    if large_changes.any():
        max_change = alt_diff.max()
        issues.append({
            "type": "large_altitude_change",
            "severity": "high" if max_change > 50 else "medium",
            "description": f"Sudden altitude change of {max_change:.1f}m detected",
            "max_change_m": float(max_change),
            "occurrences": int(large_changes.sum())
        })
    
    # Altitude spikes (sudden up then down)
    for i in range(1, len(alt) - 1):
        if (alt.iloc[i] - alt.iloc[i-1] > 15 and 
            alt.iloc[i+1] - alt.iloc[i] < -15):
            issues.append({
                "type": "altitude_spike",
                "severity": "medium",
                "description": f"Altitude spike detected at sample {i}",
                "spike_magnitude_m": float(alt.iloc[i] - alt.iloc[i-1])
            })
    
    # Negative altitude (below takeoff point)
    if alt.min() < -5:
        issues.append({
            "type": "negative_altitude",
            "severity": "high", 
            "description": f"Aircraft went below takeoff altitude: {alt.min():.1f}m",
            "min_altitude_m": float(alt.min())
        })
    
    return issues


def analyze_gps_anomalies(df: pd.DataFrame) -> list:
    """Detect GPS quality and position anomalies."""
    issues = []
    
    # HDop analysis (GPS accuracy)
    if "HDop" in df.columns:
        hdop = df["HDop"].dropna()
        if len(hdop) > 0:
            poor_gps = hdop > 3.0
            if poor_gps.any():
                avg_poor_hdop = hdop[poor_gps].mean()
                issues.append({
                    "type": "poor_gps_accuracy",
                    "severity": "high" if avg_poor_hdop > 5.0 else "medium",
                    "description": f"Poor GPS accuracy detected (HDop > 3.0)",
                    "max_hdop": float(hdop.max()),
                    "avg_poor_hdop": float(avg_poor_hdop),
                    "poor_samples": int(poor_gps.sum())
                })
    
    # Satellite count analysis
    if "NSats" in df.columns:
        nsats = df["NSats"].dropna()
        if len(nsats) > 0:
            low_sats = nsats < 6
            if low_sats.any():
                issues.append({
                    "type": "insufficient_satellites",
                    "severity": "high",
                    "description": f"Low satellite count detected (< 6 satellites)",
                    "min_satellites": int(nsats.min()),
                    "low_sat_samples": int(low_sats.sum())
                })
    
    # Position jump detection
    if "Lat" in df.columns and "Lng" in df.columns:
        lat = df["Lat"].dropna()
        lng = df["Lng"].dropna()
        if len(lat) > 1 and len(lng) > 1:
            # Calculate distance between consecutive points (rough estimate)
            lat_diff = lat.diff() * 111000  # degrees to meters (rough)
            lng_diff = lng.diff() * 111000 * np.cos(np.radians(lat.mean()))
            distance = np.sqrt(lat_diff**2 + lng_diff**2)
            
            large_jumps = distance > 100  # 100m jump
            if large_jumps.any():
                max_jump = distance.max()
                issues.append({
                    "type": "gps_position_jump",
                    "severity": "critical",
                    "description": f"Large GPS position jump detected: {max_jump:.0f}m",
                    "max_jump_m": float(max_jump),
                    "jump_count": int(large_jumps.sum())
                })
    
    return issues


def analyze_battery_anomalies(df: pd.DataFrame) -> list:
    """Detect battery and power system issues."""
    issues = []
    
    # Voltage analysis
    if "Volt" in df.columns:
        voltage = df["Volt"].dropna()
        if len(voltage) > 0:
            # Low voltage warning
            if voltage.min() < 11.1:  # Critical for 3S LiPo
                issues.append({
                    "type": "low_battery_voltage",
                    "severity": "critical",
                    "description": f"Critical low voltage detected: {voltage.min():.2f}V",
                    "min_voltage": float(voltage.min()),
                    "voltage_drop": float(voltage.max() - voltage.min())
                })
            elif voltage.min() < 11.5:  # Warning level
                issues.append({
                    "type": "low_battery_warning",
                    "severity": "medium", 
                    "description": f"Low battery warning: {voltage.min():.2f}V",
                    "min_voltage": float(voltage.min())
                })
            
            # Voltage drops (sudden decreases)
            voltage_diff = voltage.diff()
            large_drops = voltage_diff < -0.5
            if large_drops.any():
                max_drop = abs(voltage_diff.min())
                issues.append({
                    "type": "voltage_drop",
                    "severity": "medium",
                    "description": f"Sudden voltage drop detected: {max_drop:.2f}V",
                    "max_drop_v": float(max_drop),
                    "drop_count": int(large_drops.sum())
                })
    
    # Current analysis
    if "Curr" in df.columns:
        current = df["Curr"].dropna()
        if len(current) > 0:
            # High current draw
            if current.max() > 30:  # High for typical drone
                issues.append({
                    "type": "high_current_draw",
                    "severity": "medium",
                    "description": f"High current draw detected: {current.max():.1f}A",
                    "max_current_a": float(current.max()),
                    "avg_current_a": float(current.mean())
                })
    
    return issues


def analyze_control_anomalies(df: pd.DataFrame) -> list:
    """Detect control system anomalies."""
    issues = []
    
    # Attitude control analysis
    for axis in ["Roll", "Pitch", "Yaw"]:
        if axis in df.columns:
            attitude = df[axis].dropna()
            if len(attitude) > 1:
                # Large attitude changes
                attitude_diff = attitude.diff().abs()
                large_changes = attitude_diff > 30  # degrees
                if large_changes.any():
                    max_change = attitude_diff.max()
                    issues.append({
                        "type": f"{axis.lower()}_instability",
                        "severity": "high" if max_change > 60 else "medium",
                        "description": f"Large {axis} change detected: {max_change:.1f}°",
                        "max_change_deg": float(max_change),
                        "axis": axis.lower()
                    })
                
                # Check for extreme attitudes
                if attitude.abs().max() > 45:
                    issues.append({
                        "type": f"extreme_{axis.lower()}",
                        "severity": "high",
                        "description": f"Extreme {axis} attitude: {attitude.abs().max():.1f}°",
                        "max_attitude_deg": float(attitude.abs().max()),
                        "axis": axis.lower()
                    })
    
    return issues


def analyze_navigation_anomalies(df: pd.DataFrame) -> list:
    """Detect navigation system issues."""
    issues = []
    
    # Waypoint navigation analysis
    if "WPDst" in df.columns:
        wp_dist = df["WPDst"].dropna()
        if len(wp_dist) > 1:
            # Check if distance to waypoint is increasing (going away)
            increasing_dist = wp_dist.diff() > 10
            if increasing_dist.sum() > len(wp_dist) * 0.3:  # 30% of samples
                issues.append({
                    "type": "waypoint_navigation_error",
                    "severity": "medium",
                    "description": "Aircraft moving away from waypoint frequently",
                    "max_wp_distance_m": float(wp_dist.max())
                })
    
    # Climb rate analysis
    if "CRt" in df.columns:
        climb_rate = df["CRt"].dropna()
        if len(climb_rate) > 0:
            # Excessive climb/descent rates
            if climb_rate.abs().max() > 500:  # cm/s = 5 m/s
                issues.append({
                    "type": "excessive_climb_rate",
                    "severity": "high",
                    "description": f"Excessive climb rate: {climb_rate.abs().max():.0f} cm/s",
                    "max_climb_rate_cms": float(climb_rate.abs().max())
                })
    
    return issues


def analyze_system_errors(df: pd.DataFrame) -> list:
    """Detect system error messages."""
    issues = []
    
    if "msg_type" not in df.columns:
        return issues
    
    # Count error messages
    error_messages = df[df["msg_type"] == "ERR"]
    if len(error_messages) > 0:
        issues.append({
            "type": "system_errors_detected",
            "severity": "high",
            "description": f"{len(error_messages)} system error messages found",
            "error_count": len(error_messages),
            "error_types": error_messages.get("SubSys", []).unique().tolist() if "SubSys" in error_messages.columns else []
        })
    
    # Check for mode changes (could indicate pilot intervention)
    mode_messages = df[df["msg_type"] == "MODE"]
    if len(mode_messages) > 3:  # More than typical takeoff/landing
        issues.append({
            "type": "frequent_mode_changes",
            "severity": "medium", 
            "description": f"Frequent flight mode changes detected: {len(mode_messages)} changes",
            "mode_change_count": len(mode_messages)
        })
    
    return issues 