from rest_framework import serializers

from .models import PredictionData, TrafficData


class TrafficDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrafficData
        fields = ["id", "timestamp", "location", "congestion_level", "avg_speed", "incidents"]


class PredictionDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictionData
        fields = [
            "id",
            "location",
            "predicted_congestion",
            "predicted_time",
            "estimated_delay_minutes",
            "model_version",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class PredictionQuerySerializer(serializers.Serializer):
    location = serializers.CharField(max_length=255)
    horizon_minutes = serializers.IntegerField(min_value=5, max_value=1440, default=60)


class RouteQuerySerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=255)
    destination = serializers.CharField(max_length=255)
    alternatives = serializers.BooleanField(default=True)


class RouteSuggestionSerializer(serializers.Serializer):
    provider = serializers.CharField()
    origin = serializers.CharField()
    destination = serializers.CharField()
    best_route = serializers.DictField()
    alternatives = serializers.ListField(child=serializers.DictField(), required=False)
    live_traffic_available = serializers.BooleanField()
