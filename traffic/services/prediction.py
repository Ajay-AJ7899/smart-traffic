from dataclasses import dataclass
from datetime import timedelta

import numpy as np
import pandas as pd
from django.conf import settings
from django.utils import timezone

from traffic.models import CongestionLevel, PredictionData, TrafficData


CONGESTION_TO_SCORE = {
    CongestionLevel.LOW: 1.0,
    CongestionLevel.MEDIUM: 2.0,
    CongestionLevel.HIGH: 3.0,
}


@dataclass
class PredictionResult:
    location: str
    predicted_congestion: str
    predicted_time: timezone.datetime
    estimated_delay_minutes: int
    confidence: float
    model_version: str


class TrafficPredictor:
    """Time-series predictor with ARIMA when enough data exists and a robust fallback."""

    model_version = "arima-or-seasonal-baseline"

    def predict(self, location, horizon_minutes=60):
        historical = self._load_history(location)
        predicted_time = timezone.now() + timedelta(minutes=horizon_minutes)

        if len(historical) >= settings.ML_MIN_TRAINING_ROWS:
            score = self._arima_forecast(historical)
            confidence = 0.78
        else:
            score = self._seasonal_baseline(historical, predicted_time)
            confidence = 0.55 if len(historical) else 0.35

        congestion = self._score_to_level(score)
        delay = self._estimate_delay(congestion, historical)

        PredictionData.objects.create(
            location=location,
            predicted_congestion=congestion,
            predicted_time=predicted_time,
            estimated_delay_minutes=delay,
            model_version=self.model_version,
        )

        return {
            "location": location,
            "predicted_congestion": congestion,
            "predicted_time": predicted_time.isoformat(),
            "estimated_delay_minutes": delay,
            "confidence": confidence,
            "model_version": self.model_version,
            "features": {
                "horizon_minutes": horizon_minutes,
                "time_of_day": predicted_time.strftime("%H:%M"),
                "day_of_week": predicted_time.strftime("%A"),
                "training_rows": len(historical),
            },
        }

    def _load_history(self, location):
        rows = (
            TrafficData.objects.filter(location__iexact=location)
            .order_by("timestamp")
            .values("timestamp", "congestion_level", "avg_speed")
        )
        return pd.DataFrame.from_records(rows)

    def _arima_forecast(self, frame):
        try:
            from statsmodels.tsa.arima.model import ARIMA

            series = frame["congestion_level"].map(CONGESTION_TO_SCORE).astype(float)
            model = ARIMA(series, order=(1, 0, 1))
            fit = model.fit()
            forecast = fit.forecast(steps=1)
            return float(np.clip(forecast.iloc[0], 1.0, 3.0))
        except Exception:
            return self._seasonal_baseline(frame, timezone.now())

    def _seasonal_baseline(self, frame, predicted_time):
        if frame.empty:
            return self._default_score_for_time(predicted_time)

        frame = frame.copy()
        frame["hour"] = pd.to_datetime(frame["timestamp"]).dt.hour
        frame["weekday"] = pd.to_datetime(frame["timestamp"]).dt.dayofweek
        frame["score"] = frame["congestion_level"].map(CONGESTION_TO_SCORE).astype(float)
        matching = frame[
            (frame["hour"] == predicted_time.hour)
            & (frame["weekday"] == predicted_time.weekday())
        ]
        if not matching.empty:
            return float(matching["score"].mean())
        return float(frame.tail(12)["score"].mean())

    def _default_score_for_time(self, predicted_time):
        rush_hour = predicted_time.hour in {8, 9, 17, 18, 19}
        weekday = predicted_time.weekday() < 5
        return 2.4 if rush_hour and weekday else 1.5

    def _score_to_level(self, score):
        if score < 1.67:
            return CongestionLevel.LOW
        if score < 2.34:
            return CongestionLevel.MEDIUM
        return CongestionLevel.HIGH

    def _estimate_delay(self, congestion, frame):
        base_delay = {
            CongestionLevel.LOW: 5,
            CongestionLevel.MEDIUM: 15,
            CongestionLevel.HIGH: 35,
        }[congestion]
        if frame.empty:
            return base_delay

        recent_speed = float(frame.tail(6)["avg_speed"].mean())
        speed_penalty = max(0, int((40 - recent_speed) * 0.5))
        return base_delay + speed_penalty


predictor = TrafficPredictor()
