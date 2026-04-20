from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import CongestionLevel, TrafficData


class TrafficApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_ingest_high_congestion_returns_alert(self):
        response = self.client.post(
            reverse("traffic-data"),
            {
                "timestamp": timezone.now().isoformat(),
                "location": "MG Road",
                "congestion_level": CongestionLevel.HIGH,
                "avg_speed": 16.4,
                "incidents": "Lane blocked",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["alert"]["severity"], "critical")

    def test_prediction_endpoint_returns_delay(self):
        now = timezone.now()
        for index in range(12):
            TrafficData.objects.create(
                timestamp=now - timedelta(hours=12 - index),
                location="MG Road",
                congestion_level=CongestionLevel.MEDIUM,
                avg_speed=30,
            )

        response = self.client.get(reverse("predict"), {"location": "MG Road"})

        self.assertEqual(response.status_code, 200)
        self.assertIn(response.data["predicted_congestion"], ["low", "medium", "high"])
        self.assertIn("estimated_delay_minutes", response.data)

    def test_route_endpoint_has_offline_fallback(self):
        response = self.client.get(
            reverse("optimize-route"),
            {"origin": "MG Road", "destination": "Airport Road"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("best_route", response.data)
