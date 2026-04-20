import requests
from django.conf import settings


class RouteOptimizer:
    @property
    def provider_name(self):
        if settings.MAPS_PROVIDER == "google" and settings.GOOGLE_MAPS_API_KEY:
            return "google"
        if settings.MAPS_PROVIDER == "mapbox" and settings.MAPBOX_ACCESS_TOKEN:
            return "mapbox"
        return "offline"

    @property
    def browser_api_key(self):
        if self.provider_name == "google":
            return settings.GOOGLE_MAPS_API_KEY
        return ""

    def optimize(self, origin, destination, alternatives=True):
        if settings.MAPS_PROVIDER == "google" and settings.GOOGLE_MAPS_API_KEY:
            return self._google_routes(origin, destination, alternatives)
        if settings.MAPS_PROVIDER == "mapbox" and settings.MAPBOX_ACCESS_TOKEN:
            return self._mapbox_directions(origin, destination, alternatives)
        return self._fallback_route(origin, destination)

    def _google_routes(self, origin, destination, alternatives):
        response = requests.post(
            "https://routes.googleapis.com/directions/v2:computeRoutes",
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": settings.GOOGLE_MAPS_API_KEY,
                "X-Goog-FieldMask": (
                    "routes.description,"
                    "routes.distanceMeters,"
                    "routes.duration,"
                    "routes.staticDuration,"
                    "routes.polyline.encodedPolyline,"
                    "routes.localizedValues.distance,"
                    "routes.localizedValues.duration,"
                    "routes.localizedValues.staticDuration,"
                    "routes.routeLabels,"
                    "routes.warnings"
                ),
            },
            json={
                "origin": {"address": origin},
                "destination": {"address": destination},
                "travelMode": "DRIVE",
                "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
                "trafficModel": "BEST_GUESS",
                "computeAlternativeRoutes": alternatives,
                "languageCode": "en-US",
                "units": "METRIC",
            },
            timeout=8,
        )
        payload = response.json()
        if response.status_code >= 400 or payload.get("error"):
            return self._fallback_route(
                origin,
                destination,
                provider="google",
                error=self._google_error_message(payload),
            )

        routes = [self._normalize_google_route(route) for route in payload.get("routes", [])]
        routes.sort(key=lambda route: route["duration_in_traffic_seconds"])
        if not routes:
            return self._fallback_route(
                origin,
                destination,
                provider="google",
                error="Google Routes API returned no routes for the supplied origin and destination.",
            )

        return {
            "provider": "google",
            "origin": origin,
            "destination": destination,
            "best_route": routes[0] if routes else {},
            "alternatives": routes[1:],
            "live_traffic_available": bool(routes),
        }

    def _normalize_google_route(self, route):
        localized = route.get("localizedValues", {})
        return {
            "summary": route.get("description") or "Recommended route",
            "distance_text": localized.get("distance", {}).get("text")
            or self._format_distance(route.get("distanceMeters", 0)),
            "duration_text": localized.get("staticDuration", {}).get("text")
            or self._format_duration(route.get("staticDuration", "0s")),
            "duration_in_traffic_text": localized.get("duration", {}).get("text")
            or self._format_duration(route.get("duration", "0s")),
            "duration_in_traffic_seconds": self._duration_to_seconds(route.get("duration", "0s")),
            "polyline": route.get("polyline", {}).get("encodedPolyline", ""),
            "steps": route.get("warnings", []),
        }

    def _mapbox_directions(self, origin, destination, alternatives):
        return {
            "provider": "mapbox",
            "origin": origin,
            "destination": destination,
            "best_route": {
                "summary": "Mapbox optimization requires geocoded coordinates.",
                "distance_text": "N/A",
                "duration_text": "N/A",
                "duration_in_traffic_text": "N/A",
                "duration_in_traffic_seconds": 0,
                "polyline": "",
                "steps": [],
            },
            "alternatives": [],
            "live_traffic_available": False,
        }

    def _fallback_route(self, origin, destination, provider="offline", error=None):
        return {
            "provider": provider,
            "origin": origin,
            "destination": destination,
            "best_route": {
                "summary": error or "Configure GOOGLE_MAPS_API_KEY for live route optimization.",
                "distance_text": "Unavailable",
                "duration_text": "Unavailable",
                "duration_in_traffic_text": "Unavailable",
                "duration_in_traffic_seconds": 0,
                "polyline": "",
                "steps": [
                    error
                    or "Offline fallback returned because no Maps API credentials are configured."
                ],
            },
            "alternatives": [],
            "live_traffic_available": False,
        }

    def _google_error_message(self, payload):
        error = payload.get("error", {})
        return error.get("message") or "Google Routes API request failed."

    def _duration_to_seconds(self, value):
        try:
            return int(float(str(value).rstrip("s")))
        except (TypeError, ValueError):
            return 0

    def _format_duration(self, value):
        seconds = self._duration_to_seconds(value)
        minutes = max(1, round(seconds / 60))
        return f"{minutes} min"

    def _format_distance(self, meters):
        try:
            kilometers = float(meters) / 1000
        except (TypeError, ValueError):
            kilometers = 0
        return f"{kilometers:.1f} km"


route_optimizer = RouteOptimizer()
