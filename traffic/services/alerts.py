def build_alert_payload(traffic_row):
    """Return a real-time alert for newly ingested high-congestion observations."""
    if traffic_row.get("congestion_level") != "high":
        return None
    return {
        "severity": "critical",
        "message": f"High congestion detected at {traffic_row.get('location')}",
        "location": traffic_row.get("location"),
        "timestamp": traffic_row.get("timestamp"),
    }
