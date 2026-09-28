from django.utils import timezone
from rest_framework import serializers

from . import engine
from .models import NIGERIAN_STATES, Area, Status


def effective_status(area, now=None):
    """The cached status, downgraded to unknown once reports go stale."""
    now = now or timezone.now()
    if area.last_report_at is None:
        return Status.UNKNOWN, None
    stale_at = area.last_report_at + engine.STALE_AFTER
    if now >= stale_at:
        return Status.UNKNOWN, stale_at
    return area.status, area.status_since


class AreaSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    status_since = serializers.SerializerMethodField()
    reports_last_hour = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Area
        fields = ["slug", "name", "city", "state", "label", "status", "status_since", "last_report_at",
                  "reports_last_hour"]

    def get_status(self, area):
        return effective_status(area)[0]

    def get_status_since(self, area):
        return effective_status(area)[1]


class NewAreaSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    city = serializers.CharField(max_length=60)
    state = serializers.ChoiceField(choices=NIGERIAN_STATES)

    def validate_name(self, value):
        return " ".join(value.split()).title()

    def validate_city(self, value):
        return " ".join(value.split()).title()


class ReportInputSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=[Status.ON, Status.OFF])


class PushSubscriptionSerializer(serializers.Serializer):
    class Keys(serializers.Serializer):
        p256dh = serializers.CharField(max_length=200)
        auth = serializers.CharField(max_length=100)

    endpoint = serializers.URLField(max_length=600)
    keys = Keys()
