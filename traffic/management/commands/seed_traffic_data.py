from datetime import timedelta
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from traffic.models import CongestionLevel, TrafficData


class Command(BaseCommand):
    help = "Seed representative traffic observations for local development."

    def handle(self, *args, **options):
        locations = ["MG Road", "Outer Ring Road", "Electronic City", "Airport Road"]
        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        created = 0

        for hours_ago in range(96, 0, -1):
            ts = now - timedelta(hours=hours_ago)
            for location in locations:
                rush = ts.hour in {8, 9, 17, 18, 19}
                congestion = random.choices(
                    [CongestionLevel.LOW, CongestionLevel.MEDIUM, CongestionLevel.HIGH],
                    weights=[2, 5, 8] if rush else [7, 3, 1],
                )[0]
                speed = {
                    CongestionLevel.LOW: random.uniform(42, 60),
                    CongestionLevel.MEDIUM: random.uniform(24, 42),
                    CongestionLevel.HIGH: random.uniform(8, 24),
                }[congestion]
                TrafficData.objects.create(
                    timestamp=ts,
                    location=location,
                    congestion_level=congestion,
                    avg_speed=round(speed, 2),
                    incidents="Minor slowdown" if congestion == CongestionLevel.HIGH else "",
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} traffic rows."))
