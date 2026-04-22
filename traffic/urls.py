from django.urls import path

from . import views

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("traffic-data", views.TrafficDataListCreateAPIView.as_view(), name="traffic-data"),
    path("predict", views.PredictTrafficAPIView.as_view(), name="predict"),
    path("optimize-route", views.OptimizeRouteAPIView.as_view(), name="optimize-route"),
    path("peak-hours", views.PeakHourForecastAPIView.as_view(), name="peak-hours"),
    path("traffic-intensity", views.TrafficIntensityAPIView.as_view(), name="traffic-intensity"),
]
