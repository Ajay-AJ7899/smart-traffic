from django.contrib import admin

from .models import PredictionData, TrafficData


@admin.register(TrafficData)
class TrafficDataAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "location", "congestion_level", "avg_speed", "incidents")
    list_filter = ("congestion_level", "location", "timestamp")
    search_fields = ("location", "incidents")
    ordering = ("-timestamp",)


@admin.register(PredictionData)
class PredictionDataAdmin(admin.ModelAdmin):
    list_display = ("location", "predicted_congestion", "estimated_delay_minutes", "predicted_time", "created_at")
    list_filter = ("predicted_congestion", "location", "predicted_time")
    search_fields = ("location",)
    ordering = ("-created_at",)
