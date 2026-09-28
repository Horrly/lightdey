import hashlib
import hmac
import json
import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import engine
from .models import Area, PushSubscription, Report, Status

logger = logging.getLogger(__name__)

# Abuse limits. Generous enough for real people, tight enough to blunt spam.
CORRECTION_WINDOW = timedelta(minutes=10)  # re-reporting the same area updates your last report
MAX_AREAS_PER_DEVICE_PER_HOUR = 5
MAX_REPORTS_PER_IP_PER_HOUR = 40
MAX_NEW_AREAS_PER_DEVICE_PER_DAY = 3
NOTIFY_COOLDOWN = timedelta(minutes=30)


class ReportRejected(Exception):
    pass


def fingerprint(value):
    """Salted hash so raw device ids and IPs are never stored."""
    return hmac.new(settings.SECRET_KEY.encode(), (value or "").encode(), hashlib.sha256).hexdigest()


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")


def area_reports(area, start, end):
    qs = area.reports.filter(created_at__gte=start - engine.STALE_AFTER, created_at__lte=end)
    return list(qs.values_list("created_at", "state"))


def area_timeline(area, start, end):
    return engine.build_timeline(area_reports(area, start, end), start, end)


def refresh_status(area, now=None):
    """Recompute and cache the area's current status. Returns the previous status."""
    now = now or timezone.now()
    previous = area.status
    start = now - timedelta(hours=48)
    reports = area_reports(area, start, now)
    segments = engine.build_timeline(reports, start, now)
    area.status, area.status_since = engine.current_status(segments, now, reports)
    area.last_report_at = area.reports.order_by("-created_at").values_list("created_at", flat=True).first()
    area.save(update_fields=["status", "status_since", "last_report_at"])
    return previous


def record_report(*, area, state, device_id, ip, now=None):
    """Save a report (or correct the device's recent one) and update the area.

    Returns (report, created). Raises ReportRejected when limits are hit.
    """
    now = now or timezone.now()
    device_hash, ip_hash = fingerprint(device_id), fingerprint(ip)
    hour_ago = now - timedelta(hours=1)

    with transaction.atomic():
        area = Area.objects.select_for_update().get(pk=area.pk)

        recent_own = Report.objects.filter(
            area=area, device_hash=device_hash, created_at__gte=now - CORRECTION_WINDOW
        ).first()
        if recent_own:
            recent_own.state, recent_own.created_at = state, now
            recent_own.save(update_fields=["state", "created_at"])
            report, created = recent_own, False
        else:
            areas_this_hour = (
                Report.objects.filter(device_hash=device_hash, created_at__gte=hour_ago)
                .values("area").distinct().count()
            )
            if areas_this_hour >= MAX_AREAS_PER_DEVICE_PER_HOUR:
                raise ReportRejected("You've reported for many areas in the last hour. Please try again later.")
            if Report.objects.filter(ip_hash=ip_hash, created_at__gte=hour_ago).count() >= MAX_REPORTS_PER_IP_PER_HOUR:
                raise ReportRejected("Too many reports from your network. Please try again later.")
            report = Report.objects.create(
                area=area, state=state, created_at=now, device_hash=device_hash, ip_hash=ip_hash
            )
            created = True

        previous = refresh_status(area, now)
        should_notify = (
            area.status == Status.ON
            and previous != Status.ON
            and (area.last_notified_at is None or now - area.last_notified_at >= NOTIFY_COOLDOWN)
        )
        if should_notify:
            area.last_notified_at = now
            area.save(update_fields=["last_notified_at"])
            transaction.on_commit(lambda: notify_light_back(area.pk))

    return report, created


def create_area(*, name, city, state, device_id, now=None):
    now = now or timezone.now()
    device_hash = fingerprint(device_id)
    recent = Area.objects.filter(created_by_hash=device_hash, created_at__gte=now - timedelta(days=1)).count()
    if recent >= MAX_NEW_AREAS_PER_DEVICE_PER_DAY:
        raise ReportRejected("You've added several areas today. Please try again tomorrow.")
    with transaction.atomic():  # savepoint, so a duplicate doesn't break the surrounding transaction
        return Area.objects.create(name=name, city=city, state=state, created_by_hash=device_hash)


# --- Web push -------------------------------------------------------------------


def _send_push(subscription, payload):
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.VAPID_SUBJECT},
            ttl=3600,
        )
        return True
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):  # the browser unsubscribed or the subscription expired
            subscription.delete()
        else:
            logger.warning("Push to %s failed: %s", subscription.endpoint[:60], exc)
        return False


def send_light_back_notifications(area_id):
    area = Area.objects.get(pk=area_id)
    payload = {
        "title": f"💡 Light don come for {area.name}!",
        "body": f"People in {area.label} are reporting light now. Charge your phone!",
        "url": f"/a/{area.slug}",
        "tag": f"area-{area.slug}",
    }
    sent = sum(_send_push(sub, payload) for sub in area.push_subscriptions.all())
    logger.info("Light-back notifications for %s: %s sent", area.slug, sent)
    return sent


def notify_light_back(area_id):
    """Send notifications without making the reporter wait."""
    if not settings.PUSH_ENABLED:
        return
    thread = threading.Thread(target=send_light_back_notifications, args=(area_id,), daemon=True)
    thread.start()
