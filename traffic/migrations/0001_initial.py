from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PredictionData",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("location", models.CharField(db_index=True, max_length=255)),
                ("predicted_congestion", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], max_length=16)),
                ("predicted_time", models.DateTimeField(db_index=True)),
                ("estimated_delay_minutes", models.PositiveIntegerField(default=0)),
                ("model_version", models.CharField(default="baseline-arima", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-predicted_time"],
            },
        ),
        migrations.CreateModel(
            name="TrafficData",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(db_index=True)),
                ("location", models.CharField(db_index=True, max_length=255)),
                ("congestion_level", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], max_length=16)),
                ("avg_speed", models.FloatField(help_text="Average speed in km/h")),
                ("incidents", models.TextField(blank=True, default="")),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="predictiondata",
            index=models.Index(fields=["location", "predicted_time"], name="traffic_pre_locatio_80567d_idx"),
        ),
        migrations.AddIndex(
            model_name="trafficdata",
            index=models.Index(fields=["location", "timestamp"], name="traffic_tra_locatio_02547d_idx"),
        ),
        migrations.AddIndex(
            model_name="trafficdata",
            index=models.Index(fields=["congestion_level", "timestamp"], name="traffic_tra_congest_eb27f0_idx"),
        ),
    ]
