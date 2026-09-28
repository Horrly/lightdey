from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status as http
from rest_framework.response import Response
from rest_framework.views import APIView

from . import engine, services
from .models import Area, PushSubscription, Report, Status
from .serializers import (
    AreaSerializer,
    NewAreaSerializer,
    PushSubscriptionSerializer,
    ReportInputSerializer,
    effective_status,
)

MAX_RESULTS = 50


def device_id_or_400(request):
    device_id = request.headers.get("X-Device-Id", "").strip()
    if not 8 <= len(device_id) <= 100:
        return None, Response({"detail": "Missing device id."}, status=http.HTTP_400_BAD_REQUEST)
    return device_id, None


def with_activity(qs):
    hour_ago = timezone.now() - timedelta(hours=1)
    return qs.annotate(reports_last_hour=Count("reports", filter=Q(reports__created_at__gte=hour_ago)))


class AreaListView(APIView):
    """GET: search areas. POST: add a new area."""

    def get(self, request):
        qs = Area.objects.all()
        params = request.query_params
        if slugs := params.get("slugs"):
            qs = qs.filter(slug__in=[s for s in slugs.split(",") if s][:20])
        if q := params.get("q", "").strip():
            qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q) | Q(state__icontains=q))
        if city := params.get("city", "").strip():
            qs = qs.filter(city__iexact=city)
        # Areas with recent reports first, then alphabetical.
        qs = with_activity(qs).order_by(F("last_report_at").desc(nulls_last=True), "name")[:MAX_RESULTS]
        return Response(AreaSerializer(qs, many=True).data)

    def post(self, request):
        device_id, error = device_id_or_400(request)
        if error:
            return error
        data = NewAreaSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        name, city = data.validated_data["name"], data.validated_data["city"]

        existing = Area.objects.filter(name__iexact=name, city__iexact=city).first()
        if existing:
            return Response(
                {"detail": f"{existing.label} already exists.", "slug": existing.slug},
                status=http.HTTP_409_CONFLICT,
            )
        try:
            area = services.create_area(device_id=device_id, **data.validated_data)
        except services.ReportRejected as exc:
            return Response({"detail": str(exc)}, status=http.HTTP_429_TOO_MANY_REQUESTS)
        except IntegrityError:  # someone added the same area a moment ago
            existing = Area.objects.get(name__iexact=name, city__iexact=city)
            return Response({"detail": f"{existing.label} already exists.", "slug": existing.slug},
                            status=http.HTTP_409_CONFLICT)
        return Response(AreaSerializer(area).data, status=http.HTTP_201_CREATED)


class AreaDetailView(APIView):
    def get(self, request, slug):
        area = get_object_or_404(with_activity(Area.objects.all()), slug=slug)
        now = timezone.now()

        days = int(request.query_params.get("days", 7))
        days = max(1, min(days, 30))
        day_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
        history_start = day_start - timedelta(days=days - 1)
        segments = services.area_timeline(area, history_start, now)
        daily = engine.daily_hours(segments, days, now)

        last_24h = [s.as_dict() for s in segments if s.end > now - timedelta(hours=24)]
        if last_24h and last_24h[0]["start"] < now - timedelta(hours=24):
            last_24h[0]["start"] = now - timedelta(hours=24)

        hour_ago = now - timedelta(hours=1)
        recent = area.reports.filter(created_at__gte=hour_ago)

        data = AreaSerializer(area).data
        data.update({
            "timeline": last_24h,
            "daily": daily,
            "band_check": engine.band_check(daily, request.query_params.get("band")),
            "last_hour": {
                "on": recent.filter(state=Status.ON).count(),
                "off": recent.filter(state=Status.OFF).count(),
            },
            "recent_reports": list(area.reports.values("state", "created_at")[:10]),
            "push_enabled": settings.PUSH_ENABLED,
        })
        return Response(data)


class ReportView(APIView):
    def post(self, request, slug):
        device_id, error = device_id_or_400(request)
        if error:
            return error
        area = get_object_or_404(Area, slug=slug)
        data = ReportInputSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            _, created = services.record_report(
                area=area, state=data.validated_data["state"], device_id=device_id, ip=services.client_ip(request)
            )
        except services.ReportRejected as exc:
            return Response({"detail": str(exc)}, status=http.HTTP_429_TOO_MANY_REQUESTS)

        area = with_activity(Area.objects.all()).get(pk=area.pk)
        return Response(
            {"created": created, "area": AreaSerializer(area).data},
            status=http.HTTP_201_CREATED if created else http.HTTP_200_OK,
        )


class OverviewView(APIView):
    """What the home page shows: totals, per-city counts and a live feed."""

    def get(self, request):
        now = timezone.now()
        cities = {}
        totals = {Status.ON: 0, Status.OFF: 0, Status.UNKNOWN: 0}
        for area in Area.objects.only("city", "state", "status", "status_since", "last_report_at"):
            state, _ = effective_status(area, now)
            totals[state] += 1
            key = (area.city, area.state)
            city = cities.setdefault(key, {"city": area.city, "state": area.state, "on": 0, "off": 0, "unknown": 0})
            city[state] += 1

        feed = (
            Report.objects.filter(created_at__gte=now - timedelta(hours=6))
            .select_related("area")
            .order_by("-created_at")[:15]
        )
        return Response({
            "totals": totals,
            "cities": sorted(cities.values(), key=lambda c: (-(c["on"] + c["off"]), c["city"])),
            "feed": [
                {"area": r.area.label, "slug": r.area.slug, "state": r.state, "created_at": r.created_at}
                for r in feed
            ],
            "reports_today": Report.objects.filter(
                created_at__gte=timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)
            ).count(),
        })


class PushConfigView(APIView):
    def get(self, request):
        return Response({"enabled": settings.PUSH_ENABLED, "public_key": settings.VAPID_PUBLIC_KEY or None})


class PushSubscribeView(APIView):
    def post(self, request, slug):
        if not settings.PUSH_ENABLED:
            return Response({"detail": "Notifications aren't set up on this server."}, status=http.HTTP_404_NOT_FOUND)
        area = get_object_or_404(Area, slug=slug)
        data = PushSubscriptionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        sub, created = PushSubscription.objects.update_or_create(
            area=area,
            endpoint=data.validated_data["endpoint"],
            defaults={"p256dh": data.validated_data["keys"]["p256dh"], "auth": data.validated_data["keys"]["auth"]},
        )
        return Response({"subscribed": True}, status=http.HTTP_201_CREATED if created else http.HTTP_200_OK)

    def delete(self, request, slug):
        area = get_object_or_404(Area, slug=slug)
        endpoint = request.data.get("endpoint", "")
        deleted, _ = PushSubscription.objects.filter(area=area, endpoint=endpoint).delete()
        return Response({"subscribed": False, "removed": deleted})
