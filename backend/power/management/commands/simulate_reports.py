"""DEV ONLY: fill a local database with made-up reports for screenshots and UI work.

Refuses to run when DEBUG is off, so fake data can never reach the live site.
"""

import random
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from power.models import Area, Report
from power.services import fingerprint, refresh_status


class Command(BaseCommand):
    help = "DEV ONLY: generate random reports for the last few days."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7)
        parser.add_argument("--areas", type=int, default=25)
        parser.add_argument("--seed", type=int, default=7)

    def handle(self, *args, days, areas, seed, **options):
        if not settings.DEBUG:
            raise CommandError("simulate_reports only runs with DEBUG=True. Never fake data on the live site.")
        rng = random.Random(seed)
        now = timezone.now()
        chosen = list(Area.objects.order_by("id")[:areas])
        for area in chosen:
            reliability = rng.uniform(0.25, 0.85)  # share of time with light
            t = now - timedelta(days=days)
            state = "on" if rng.random() < reliability else "off"
            reports = []
            while t < now:
                # Stretches of supply or outage, reported by a few people each.
                duration = timedelta(minutes=rng.randint(40, 300))
                for _ in range(rng.randint(1, 4)):
                    at = t + timedelta(minutes=rng.randint(0, max(1, int(duration.total_seconds() // 60) - 1)))
                    if at < now:
                        reports.append(Report(area=area, state=state, created_at=at,
                                              device_hash=fingerprint(str(rng.random())), ip_hash=fingerprint("sim")))
                t += duration
                state = "on" if rng.random() < reliability else "off"
            Report.objects.bulk_create(reports)
            refresh_status(area, now)
        self.stdout.write(f"Simulated reports for {len(chosen)} areas over {days} days.")
