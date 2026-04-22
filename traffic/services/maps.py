import requests
from django.conf import settings
from requests import RequestException


class RouteOptimizer:
    @property
    def provider_name(self):
        if settings.MAPS_PROVIDER == "geoapify" and settings.GEOAPIFY_API_KEY:
            return "geoapify"
        if settings.MAPS_PROVIDER in {"openrouteservice", "ors"} and settings.OPENROUTESERVICE_API_KEY:
            return "openrouteservice"
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

    @property
    def geoapify_browser_api_key(self):
        if self.provider_name == "geoapify":
            return settings.GEOAPIFY_API_KEY
        return ""

    def optimize(self, origin, destination, alternatives=True):
        if settings.MAPS_PROVIDER == "geoapify" and settings.GEOAPIFY_API_KEY:
            return self._geoapify_route(origin, destination)
        if settings.MAPS_PROVIDER in {"openrouteservice", "ors"} and settings.OPENROUTESERVICE_API_KEY:
            return self._openrouteservice_route(origin, destination)
        if settings.MAPS_PROVIDER == "google" and settings.GOOGLE_MAPS_API_KEY:
            return self._google_routes(origin, destination, alternatives)
        if settings.MAPS_PROVIDER == "mapbox" and settings.MAPBOX_ACCESS_TOKEN:
            return self._mapbox_directions(origin, destination, alternatives)
        return self._fallback_route(origin, destination)

    def _geoapify_route(self, origin, destination):
        try:
            origin_coordinates = self._geoapify_geocode(origin)
            destination_coordinates = self._geoapify_geocode(destination)
            response = self._external_session().get(
                "https://api.geoapify.com/v1/routing",
                params={
                    "waypoints": (
                        f"{origin_coordinates[0]},{origin_coordinates[1]}|"
                        f"{destination_coordinates[0]},{destination_coordinates[1]}"
                    ),
                    "mode": "drive",
                    "apiKey": settings.GEOAPIFY_API_KEY,
                },
                timeout=12,
            )
            payload = response.json()
        except (RequestException, ValueError, KeyError, IndexError) as exc:
            return self._fallback_route(
                origin,
                destination,
                provider="geoapify",
                error=f"Geoapify routing is unavailable: {exc}",
            )

        if response.status_code >= 400 or "error" in payload:
            return self._fallback_route(
                origin,
                destination,
                provider="geoapify",
                error=self._routing_error_message(payload, "Geoapify route request failed."),
            )

        features = payload.get("features", [])
        if not features:
            return self._fallback_route(
                origin,
                destination,
                provider="geoapify",
                error="Geoapify returned no route for these places.",
            )

        best_route = self._normalize_geoapify_route(features[0])
        return {
            "provider": "geoapify",
            "origin": origin,
            "destination": destination,
            "best_route": best_route,
            "alternatives": [],
            "live_traffic_available": False,
            "real_route_available": bool(best_route["geometry"]["coordinates"]),
        }

    def _geoapify_geocode(self, place):
        response = self._external_session().get(
            "https://api.geoapify.com/v1/geocode/search",
            params={
                "text": self._localize_place(place),
                "format": "json",
                "limit": 1,
                "filter": "countrycode:in",
                "apiKey": settings.GEOAPIFY_API_KEY,
            },
            timeout=12,
        )
        payload = response.json()
        if response.status_code >= 400 or "error" in payload:
            raise ValueError(self._routing_error_message(payload, "Geoapify geocoding failed."))
        result = payload["results"][0]
        return [result["lat"], result["lon"]]

    def _normalize_geoapify_route(self, route):
        properties = route.get("properties", {})
        geometry = route.get("geometry", {})
        coordinates = self._geojson_coordinates_to_lat_lon(geometry.get("coordinates", []))
        duration_seconds = properties.get("time", 0)
        distance_meters = properties.get("distance", 0)
        steps = []
        for leg in properties.get("legs", []):
            for step in leg.get("steps", []):
                instruction = step.get("instruction", {})
                text = instruction.get("text") if isinstance(instruction, dict) else None
                if text:
                    steps.append(text)

        return {
            "summary": "Real driving route",
            "distance_text": self._format_distance(distance_meters),
            "duration_text": self._format_duration(f"{duration_seconds}s"),
            "duration_in_traffic_text": self._format_duration(f"{duration_seconds}s"),
            "duration_in_traffic_seconds": self._duration_to_seconds(f"{duration_seconds}s"),
            "polyline": "",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates,
            },
            "steps": steps[:8],
        }

    def _openrouteservice_route(self, origin, destination):
        try:
            origin_coordinates = self._openrouteservice_geocode(origin)
            destination_coordinates = self._openrouteservice_geocode(destination)
            response = self._external_session().post(
                "https://api.openrouteservice.org/v2/directions/driving-car/geojson",
                headers={
                    "Authorization": settings.OPENROUTESERVICE_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "coordinates": [origin_coordinates, destination_coordinates],
                    "instructions": True,
                },
                timeout=12,
            )
            payload = response.json()
        except (RequestException, ValueError, KeyError, IndexError) as exc:
            return self._fallback_route(
                origin,
                destination,
                provider="openrouteservice",
                error=f"OpenRouteService routing is unavailable: {exc}",
            )

        if response.status_code >= 400 or "error" in payload:
            return self._fallback_route(
                origin,
                destination,
                provider="openrouteservice",
                error=self._routing_error_message(payload, "OpenRouteService route request failed."),
            )

        features = payload.get("features", [])
        if not features:
            return self._fallback_route(
                origin,
                destination,
                provider="openrouteservice",
                error="OpenRouteService returned no route for these places.",
            )

        best_route = self._normalize_openrouteservice_route(features[0])
        return {
            "provider": "openrouteservice",
            "origin": origin,
            "destination": destination,
            "best_route": best_route,
            "alternatives": [],
            "live_traffic_available": False,
            "real_route_available": bool(best_route["geometry"]["coordinates"]),
        }

    def _openrouteservice_geocode(self, place):
        query = self._localize_place(place)
        response = self._external_session().get(
            "https://api.openrouteservice.org/geocode/search",
            params={
                "api_key": settings.OPENROUTESERVICE_API_KEY,
                "text": query,
                "size": 1,
                "boundary.country": "IN",
            },
            timeout=12,
        )
        payload = response.json()
        if response.status_code >= 400 or "error" in payload:
            raise ValueError(self._routing_error_message(payload, "OpenRouteService geocoding failed."))
        return payload["features"][0]["geometry"]["coordinates"]

    def _normalize_openrouteservice_route(self, route):
        properties = route.get("properties", {})
        summary = properties.get("summary", {})
        distance_meters = summary.get("distance", 0)
        duration_seconds = summary.get("duration", 0)
        coordinates = route.get("geometry", {}).get("coordinates", [])
        steps = []
        for segment in properties.get("segments", []):
            for step in segment.get("steps", []):
                instruction = step.get("instruction")
                if instruction:
                    steps.append(instruction)

        return {
            "summary": "Real driving route",
            "distance_text": self._format_distance(distance_meters),
            "duration_text": self._format_duration(f"{duration_seconds}s"),
            "duration_in_traffic_text": self._format_duration(f"{duration_seconds}s"),
            "duration_in_traffic_seconds": self._duration_to_seconds(f"{duration_seconds}s"),
            "polyline": "",
            "geometry": {
                "type": "LineString",
                "coordinates": [[lat, lon] for lon, lat in coordinates],
            },
            "steps": steps[:8],
        }

    def _google_routes(self, origin, destination, alternatives):
        try:
            response = self._external_session().post(
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
        except RequestException as exc:
            return self._fallback_route(
                origin,
                destination,
                provider="google",
                error="Live Google route optimization is unavailable right now.",
            )

        try:
            payload = response.json()
        except ValueError:
            payload = {}

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
            "real_route_available": False,
        }

    def _fallback_route(self, origin, destination, provider="offline", error=None):
        estimated_distance_km = self._estimate_distance_km(origin, destination)
        estimated_duration_minutes = self._estimate_duration_minutes(estimated_distance_km)
        summary = error or "Local route estimate"

        return {
            "provider": provider,
            "origin": origin,
            "destination": destination,
            "best_route": {
                "summary": summary,
                "distance_text": f"{estimated_distance_km:.1f} km",
                "duration_text": f"{estimated_duration_minutes} min",
                "duration_in_traffic_text": f"{estimated_duration_minutes} min",
                "duration_in_traffic_seconds": estimated_duration_minutes * 60,
                "polyline": "",
                "steps": [
                    "Showing a local estimate because live traffic routing is not available."
                ],
            },
            "alternatives": [],
            "live_traffic_available": False,
            "real_route_available": False,
        }

    def _google_error_message(self, payload):
        error = payload.get("error", {})
        return error.get("message") or "Google Routes API request failed."

    def _routing_error_message(self, payload, default):
        error = payload.get("error", {})
        if isinstance(error, dict):
            return error.get("message") or default
        if isinstance(error, str):
            return error
        if payload.get("message"):
            return payload["message"]
        return default

    def _external_session(self):
        session = requests.Session()
        session.trust_env = False
        return session

    def _localize_place(self, place):
        if "," in place:
            return place
        return f"{place}, Bengaluru, Karnataka, India"

    def _geojson_coordinates_to_lat_lon(self, coordinates):
        if not coordinates:
            return []
        first = coordinates[0]
        if isinstance(first, (int, float)) and len(coordinates) >= 2:
            lon, lat = coordinates[:2]
            return [[lat, lon]]
        flattened = []
        for item in coordinates:
            flattened.extend(self._geojson_coordinates_to_lat_lon(item))
        return flattened

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

    def _estimate_distance_km(self, origin, destination):
        known_routes = {
            ("mg road", "airport road"): 34.0,
            ("airport road", "mg road"): 34.0,
            ("mg road", "outer ring"): 12.5,
            ("outer ring", "mg road"): 12.5,
            ("mg road", "electronic city"): 21.0,
            ("electronic city", "mg road"): 21.0,
            ("outer ring", "airport road"): 28.0,
            ("airport road", "outer ring"): 28.0,
            ("electronic city", "airport road"): 47.0,
            ("airport road", "electronic city"): 47.0,
        }
        key = (origin.strip().lower(), destination.strip().lower())
        if key in known_routes:
            return known_routes[key]

        route_seed = sum(ord(char) for char in f"{origin}:{destination}")
        return 6.0 + (route_seed % 320) / 10

    def _estimate_duration_minutes(self, distance_km):
        return max(8, round((distance_km / 28) * 60))


route_optimizer = RouteOptimizer()
