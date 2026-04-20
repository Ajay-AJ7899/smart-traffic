from pathlib import Path

import joblib
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from statsmodels.tsa.arima.model import ARIMA

from traffic.models import TrafficData
from traffic.services.prediction import CONGESTION_TO_SCORE


class Command(BaseCommand):
    help = "Train an ARIMA traffic congestion model from stored historical traffic data."

    def add_arguments(self, parser):
        parser.add_argument("--location", help="Train with data for one location only.")

    def handle(self, *args, **options):
        queryset = TrafficData.objects.order_by("timestamp")
        if options.get("location"):
            queryset = queryset.filter(location__iexact=options["location"])

        frame = pd.DataFrame.from_records(
            queryset.values("timestamp", "location", "congestion_level", "avg_speed")
        )
        if len(frame) < settings.ML_MIN_TRAINING_ROWS:
            self.stderr.write(
                self.style.ERROR(
                    f"Need at least {settings.ML_MIN_TRAINING_ROWS} rows, found {len(frame)}."
                )
            )
            return

        series = frame["congestion_level"].map(CONGESTION_TO_SCORE).astype(float)
        model = ARIMA(series, order=(1, 0, 1)).fit()
        Path(settings.ML_MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": model, "rows": len(frame)}, settings.ML_MODEL_PATH)
        self.stdout.write(self.style.SUCCESS(f"Saved model to {settings.ML_MODEL_PATH}"))
