from django.shortcuts import render
from django.views import View
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TrafficData
from .serializers import (
    PredictionQuerySerializer,
    RouteQuerySerializer,
    TrafficDataSerializer,
)
from .services.alerts import build_alert_payload
from .services.maps import route_optimizer
from .services.prediction import predictor


class DashboardView(View):
    def get(self, request):
        return render(
            request,
            "traffic/dashboard.html",
            {
                "maps_provider": route_optimizer.provider_name,
                "google_maps_api_key": route_optimizer.browser_api_key,
            },
        )


class TrafficDataListCreateAPIView(generics.ListCreateAPIView):
    queryset = TrafficData.objects.all()
    serializer_class = TrafficDataSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        location = self.request.query_params.get("location")
        if location:
            queryset = queryset.filter(location__icontains=location)
        return queryset

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        alert = build_alert_payload(response.data)
        response.data["alert"] = alert
        return response


class PredictTrafficAPIView(APIView):
    def get(self, request):
        serializer = PredictionQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        prediction = predictor.predict(
            location=serializer.validated_data["location"],
            horizon_minutes=serializer.validated_data["horizon_minutes"],
        )
        return Response(prediction, status=status.HTTP_200_OK)


class OptimizeRouteAPIView(APIView):
    def get(self, request):
        serializer = RouteQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        route = route_optimizer.optimize(
            origin=serializer.validated_data["origin"],
            destination=serializer.validated_data["destination"],
            alternatives=serializer.validated_data["alternatives"],
        )
        return Response(route, status=status.HTTP_200_OK)
