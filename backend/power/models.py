from django.db import models
from django.utils.crypto import get_random_string
from django.utils.text import slugify

NIGERIAN_STATES = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno",
    "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "FCT", "Gombe", "Imo",
    "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa",
    "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba",
    "Yobe", "Zamfara",
]


class Status(models.TextChoices):
    ON = "on", "Light dey"
    OFF = "off", "No light"
    UNKNOWN = "unknown", "No recent reports"


class Area(models.Model):
    """A neighbourhood people report for, e.g. "Yaba, Lagos".

    `status`, `status_since` and `last_report_at` are a cache of the latest
    computed state (see engine.py), so listing hundreds of areas stays cheap.
    """

    name = models.CharField(max_length=80)
    city = models.CharField(max_length=60)
    state = models.CharField(max_length=20, choices=[(s, s) for s in NIGERIAN_STATES])
    slug = models.SlugField(max_length=160, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by_hash = models.CharField(max_length=64, blank=True, db_index=True)

    status = models.CharField(max_length=8, choices=Status.choices, default=Status.UNKNOWN)
    status_since = models.DateTimeField(null=True, blank=True)
    last_report_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                models.functions.Lower("name"), models.functions.Lower("city"), name="unique_area_per_city"
            ),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.name} {self.city}")[:140] or "area"
            slug = base
            while Area.objects.filter(slug=slug).exists():
                slug = f"{base}-{get_random_string(4).lower()}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def label(self):
        return self.name if self.name.lower() == self.city.lower() else f"{self.name}, {self.city}"

    def __str__(self):
        return self.label


class Report(models.Model):
    """One person saying "light dey" or "no light" for an area at a moment.

    Reporters are anonymous. We only keep salted hashes of a random per-browser
    id and of the IP address, which is enough for rate limiting.
    """

    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="reports")
    state = models.CharField(max_length=3, choices=[(Status.ON, "On"), (Status.OFF, "Off")])
    created_at = models.DateTimeField(db_index=True)
    device_hash = models.CharField(max_length=64, db_index=True)
    ip_hash = models.CharField(max_length=64, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["area", "created_at"])]


class PushSubscription(models.Model):
    """A browser that wants a notification when light returns to an area."""

    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="push_subscriptions")
    endpoint = models.URLField(max_length=600)
    p256dh = models.CharField(max_length=200)
    auth = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["area", "endpoint"], name="unique_subscription_per_area"),
        ]
