"""
Peak hour forecast & traffic intensity service.

Computes:
 - 24-hour congestion forecast for a specific location (for the bar chart)
 - Live intensity score + coordinates for all known locations (for map circles)
"""

from __future__ import annotations

from datetime import datetime, timezone as tz
from typing import Any

import pandas as pd

from traffic.models import CongestionLevel, TrafficData

# ── Known Bangalore locations with GPS coordinates ───────────────────────────
LOCATION_META: dict[str, dict[str, Any]] = {
    "MG Road":          {"lat": 12.9753, "lon": 77.6063, "radius_base": 500},
    "Airport Road":     {"lat": 12.9591, "lon": 77.6490, "radius_base": 600},
    "Outer Ring Road":  {"lat": 12.9344, "lon": 77.6101, "radius_base": 700},
    "Electronic City":  {"lat": 12.8390, "lon": 77.6770, "radius_base": 650},
}

# Canonical name lookup (lowercase → display name)
_LOCATION_LOOKUP: dict[str, str] = {k.lower(): k for k in LOCATION_META}

# Congestion → numeric score
CONG_SCORE = {
    CongestionLevel.LOW:    1.0,
    CongestionLevel.MEDIUM: 2.0,
    CongestionLevel.HIGH:   3.0,
}

# Score → level string
def _score_to_level(score: float) -> str:
    if score < 1.67:
        return CongestionLevel.LOW
    if score < 2.34:
        return CongestionLevel.MEDIUM
    return CongestionLevel.HIGH


def _score_to_intensity(score: float) -> float:
    """Return 0.0–1.0 intensity (for circle radius scaling)."""
    return round((min(max(score, 1.0), 3.0) - 1.0) / 2.0, 3)


# ── Seasonal baseline (no historical data) ───────────────────────────────────
_WEEKDAY_PEAK = {
    0: 2.4, 1: 2.4, 2: 2.4, 3: 2.4, 4: 2.5, 5: 1.8, 6: 1.5,  # day-of-week
}

_HOUR_PROFILE = {
    0: 1.0, 1: 1.0, 2: 1.0, 3: 1.0, 4: 1.1, 5: 1.3,
    6: 1.7, 7: 2.1, 8: 2.6, 9: 2.7, 10: 2.3, 11: 2.0,
    12: 2.1, 13: 2.0, 14: 1.9, 15: 2.0, 16: 2.2, 17: 2.7,
    18: 2.8, 19: 2.6, 20: 2.2, 21: 1.8, 22: 1.4, 23: 1.1,
}

def _baseline_score(hour: int, weekday: int = 1) -> float:
    h = _HOUR_PROFILE.get(hour, 1.5)
    d = _WEEKDAY_PEAK.get(weekday, 2.0)
    return round(min(h * (d / 2.0), 3.0), 3)


# ── Core: hourly forecast for a location ────────────────────────────────────
def peak_hour_forecast(location: str) -> dict[str, Any]:
    """
    Return a 24-element list (hours 0–23) with predicted congestion
    score, level, and intensity for `location`.
    """
    canonical = _LOCATION_LOOKUP.get(location.strip().lower(), location.strip())

    rows = (
        TrafficData.objects
        .filter(location__iexact=canonical)
        .values("timestamp", "congestion_level", "avg_speed")
    )
    df = pd.DataFrame.from_records(rows)

    now = datetime.now(tz.utc)
    today_weekday = now.weekday()

    hourly: list[dict[str, Any]] = []

    if not df.empty:
        df["hour"]    = pd.to_datetime(df["timestamp"], utc=True).dt.hour
        df["weekday"] = pd.to_datetime(df["timestamp"], utc=True).dt.dayofweek
        df["score"]   = df["congestion_level"].map(CONG_SCORE).astype(float)

        # Group by hour and take a weighted average (recent data counts more)
        hour_groups = df.groupby("hour")["score"].mean().to_dict()

        for h in range(24):
            if h in hour_groups:
                score = round(float(hour_groups[h]), 3)
            else:
                score = _baseline_score(h, today_weekday)

            level     = _score_to_level(score)
            intensity = _score_to_intensity(score)
            hourly.append({
                "hour":      h,
                "label":     f"{h:02d}:00",
                "score":     score,
                "level":     level,
                "intensity": intensity,
                "is_peak":   score >= 2.4,
            })
    else:
        for h in range(24):
            score     = _baseline_score(h, today_weekday)
            level     = _score_to_level(score)
            intensity = _score_to_intensity(score)
            hourly.append({
                "hour":      h,
                "label":     f"{h:02d}:00",
                "score":     score,
                "level":     level,
                "intensity": intensity,
                "is_peak":   score >= 2.4,
            })

    # Compute summary stats
    peak_hours   = [e["label"] for e in hourly if e["is_peak"]]
    max_entry    = max(hourly, key=lambda x: x["score"])
    min_entry    = min(hourly, key=lambda x: x["score"])
    current_hour = now.hour
    current_fc   = hourly[current_hour]

    return {
        "location":     canonical,
        "hourly":       hourly,
        "peak_hours":   peak_hours,
        "worst_hour":   max_entry["label"],
        "best_hour":    min_entry["label"],
        "current_hour": current_fc,
        "data_source":  "historical" if not df.empty else "seasonal_baseline",
    }


# ── Core: intensity for all locations (for map circles) ─────────────────────
def all_locations_intensity() -> list[dict[str, Any]]:
    """
    Return current congestion intensity for every known location.
    Pulls the latest TrafficData row per location; falls back to
    the seasonal baseline for the current hour.
    """
    now  = datetime.now(tz.utc)
    hour = now.hour
    wday = now.weekday()

    result: list[dict[str, Any]] = []

    for display_name, meta in LOCATION_META.items():
        latest = (
            TrafficData.objects
            .filter(location__iexact=display_name)
            .order_by("-timestamp")
            .values("congestion_level", "avg_speed", "timestamp")
            .first()
        )

        if latest:
            score     = CONG_SCORE.get(latest["congestion_level"], 1.5)
            level     = latest["congestion_level"]
            avg_speed = latest["avg_speed"]
            source    = "live"
        else:
            score     = _baseline_score(hour, wday)
            level     = _score_to_level(score)
            avg_speed = None
            source    = "baseline"

        intensity   = _score_to_intensity(score)
        radius_m    = int(meta["radius_base"] * (0.5 + intensity))   # 50–100% of base

        result.append({
            "location":  display_name,
            "lat":       meta["lat"],
            "lon":       meta["lon"],
            "level":     level,
            "score":     round(score, 2),
            "intensity": intensity,
            "radius_m":  radius_m,
            "avg_speed": avg_speed,
            "source":    source,
        })

    return result
