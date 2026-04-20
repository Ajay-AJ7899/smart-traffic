from django.db import models


class CongestionLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class TrafficData(models.Model):
    timestamp = models.DateTimeField(db_index=True)
    location = models.CharField(max_length=255, db_index=True)
    congestion_level = models.CharField(max_length=16, choices=CongestionLevel.choices)
    avg_speed = models.FloatField(help_text="Average speed in km/h")
    incidents = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["location", "timestamp"]),
            models.Index(fields=["congestion_level", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.location} - {self.congestion_level} at {self.timestamp}"


class PredictionData(models.Model):
    location = models.CharField(max_length=255, db_index=True)
    predicted_congestion = models.CharField(max_length=16, choices=CongestionLevel.choices)
    predicted_time = models.DateTimeField(db_index=True)
    estimated_delay_minutes = models.PositiveIntegerField(default=0)
    model_version = models.CharField(max_length=64, default="baseline-arima")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-predicted_time"]
        indexes = [
            models.Index(fields=["location", "predicted_time"]),
        ]

    def __str__(self):
        return f"{self.location} - {self.predicted_congestion} for {self.predicted_time}"
