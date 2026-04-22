from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from requests import RequestException
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

    @patch("traffic.services.maps.requests.post")
    def test_route_endpoint_falls_back_when_google_is_unreachable(self, mock_post):
        mock_post.side_effect = RequestException("connection failed")

        with self.settings(MAPS_PROVIDER="google", GOOGLE_MAPS_API_KEY="test-key"):
            response = self.client.get(
                reverse("optimize-route"),
                {"origin": "MG Road", "destination": "Airport Road"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], "google")
        self.assertFalse(response.data["live_traffic_available"])
        self.assertEqual(
            response.data["best_route"]["summary"],
            "Live Google route optimization is unavailable right now.",
        )
        self.assertNotEqual(response.data["best_route"]["distance_text"], "Unavailable")

    @patch("traffic.services.maps.requests.Session")
    def test_route_endpoint_returns_openrouteservice_geometry(self, mock_session):
        session = mock_session.return_value
        session.get.side_effect = [
            self._mock_response(
                {
                    "features": [
                        {"geometry": {"coordinates": [77.6101, 12.9754]}},
                    ]
                }
            ),
            self._mock_response(
                {
                    "features": [
                        {"geometry": {"coordinates": [77.7066, 13.1986]}},
                    ]
                }
            ),
        ]
        session.post.return_value = self._mock_response(
            {
                "features": [
                    {
                        "geometry": {
                            "coordinates": [
                                [77.6101, 12.9754],
                                [77.6500, 13.0500],
                                [77.7066, 13.1986],
                            ]
                        },
                        "properties": {
                            "summary": {"distance": 34200, "duration": 4380},
                            "segments": [
                                {
                                    "steps": [
                                        {"instruction": "Head north"},
                                        {"instruction": "Continue to Airport Road"},
                                    ]
                                }
                            ],
                        },
                    }
                ]
            }
        )

        with self.settings(MAPS_PROVIDER="openrouteservice", OPENROUTESERVICE_API_KEY="test-key"):
            response = self.client.get(
                reverse("optimize-route"),
                {"origin": "MG Road", "destination": "Airport Road"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], "openrouteservice")
        self.assertTrue(response.data["real_route_available"])
        self.assertEqual(response.data["best_route"]["distance_text"], "34.2 km")
        self.assertEqual(
            response.data["best_route"]["geometry"]["coordinates"][0],
            [12.9754, 77.6101],
        )

    @patch("traffic.services.maps.requests.Session")
    def test_route_endpoint_returns_geoapify_geometry(self, mock_session):
        session = mock_session.return_value
        session.get.side_effect = [
            self._mock_response({"results": [{"lat": 12.9754, "lon": 77.6101}]}),
            self._mock_response({"results": [{"lat": 13.1986, "lon": 77.7066}]}),
            self._mock_response(
                {
                    "features": [
                        {
                            "geometry": {
                                "type": "LineString",
                                "coordinates": [
                                    [77.6101, 12.9754],
                                    [77.6500, 13.0500],
                                    [77.7066, 13.1986],
                                ],
                            },
                            "properties": {
                                "distance": 34200,
                                "time": 4380,
                                "legs": [
                                    {
                                        "steps": [
                                            {"instruction": {"text": "Head north"}},
                                        ]
                                    }
                                ],
                            },
                        }
                    ]
                }
            ),
        ]

        with self.settings(MAPS_PROVIDER="geoapify", GEOAPIFY_API_KEY="test-key"):
            response = self.client.get(
                reverse("optimize-route"),
                {"origin": "MG Road", "destination": "Airport Road"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], "geoapify")
        self.assertTrue(response.data["real_route_available"])
        self.assertEqual(response.data["best_route"]["distance_text"], "34.2 km")
        self.assertEqual(
            response.data["best_route"]["geometry"]["coordinates"][-1],
            [13.1986, 77.7066],
        )

    def _mock_response(self, payload, status_code=200):
        class MockResponse:
            def __init__(self, data, status):
                self.data = data
                self.status_code = status

            def json(self):
                return self.data

        return MockResponse(payload, status_code)
