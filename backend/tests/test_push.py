import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

import pytest
from django.core.management import call_command
from django.utils import timezone

from power import services
from power.models import PushSubscription

pytestmark = pytest.mark.django_db

SUB = {"endpoint": "https://push.example.com/abc", "keys": {"p256dh": "BPkey", "auth": "authkey"}}


@pytest.fixture
def vapid(settings):
    settings.VAPID_PUBLIC_KEY = "public"
    settings.VAPID_PRIVATE_KEY = "private"
    settings.PUSH_ENABLED = True


def test_config_endpoint(api, settings):
    assert api.get("/api/push/config/").data == {"enabled": False, "public_key": None}


def test_subscribe_and_unsubscribe(api, yaba, vapid):
    assert api.post(f"/api/areas/{yaba.slug}/push/", SUB, format="json").status_code == 201
    assert api.post(f"/api/areas/{yaba.slug}/push/", SUB, format="json").status_code == 200  # idempotent
    assert PushSubscription.objects.count() == 1

    res = api.delete(f"/api/areas/{yaba.slug}/push/", {"endpoint": SUB["endpoint"]}, format="json")
    assert res.data["removed"] == 1


def test_subscribe_disabled_without_keys(api, yaba):
    assert api.post(f"/api/areas/{yaba.slug}/push/", SUB, format="json").status_code == 404


def test_light_back_triggers_one_notification(report, yaba, make_client, vapid, django_capture_on_commit_callbacks):
    with mock.patch.object(services, "notify_light_back") as notify:
        with django_capture_on_commit_callbacks(execute=True):
            report(yaba, "off")
        notify.assert_not_called()  # outages don't notify

        with django_capture_on_commit_callbacks(execute=True):
            report(yaba, "on", client=make_client())
            report(yaba, "on", client=make_client())  # still on: no second notification
        assert notify.call_count == 1


def test_notification_cooldown(report, yaba, make_client, vapid, django_capture_on_commit_callbacks):
    with mock.patch.object(services, "notify_light_back") as notify:
        with django_capture_on_commit_callbacks(execute=True):
            report(yaba, "on", client=make_client("device-11111111"))
            report(yaba, "off", client=make_client("device-22222222"))
            report(yaba, "off", client=make_client("device-33333333"))
            report(yaba, "on", client=make_client("device-44444444"))
            report(yaba, "on", client=make_client("device-55555555"))  # flips back on within 30 min
        assert notify.call_count == 1


def test_expired_subscriptions_are_removed(yaba, vapid):
    from pywebpush import WebPushException

    PushSubscription.objects.create(area=yaba, endpoint="https://push.example.com/gone", p256dh="k", auth="a")
    PushSubscription.objects.create(area=yaba, endpoint="https://push.example.com/ok", p256dh="k", auth="a")

    def fake_webpush(subscription_info, **kwargs):
        if subscription_info["endpoint"].endswith("gone"):
            raise WebPushException("gone", response=mock.Mock(status_code=410))

    with mock.patch("pywebpush.webpush", side_effect=fake_webpush):
        assert services.send_light_back_notifications(yaba.id) == 1
    assert list(PushSubscription.objects.values_list("endpoint", flat=True)) == ["https://push.example.com/ok"]


def test_generated_vapid_keys_really_sign_pushes(settings, yaba, capsys):
    """End to end with real crypto: generate keys, send to a local fake push service."""
    import base64

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    call_command("generate_vapid_keys")
    out = capsys.readouterr().out
    keys = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    settings.VAPID_PUBLIC_KEY, settings.VAPID_PRIVATE_KEY = keys["VAPID_PUBLIC_KEY"], keys["VAPID_PRIVATE_KEY"]
    settings.PUSH_ENABLED = True

    received = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            received["auth"] = self.headers.get("Authorization")
            received["body"] = self.rfile.read(int(self.headers["Content-Length"]))
            self.send_response(201)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()

    # A browser's subscription keys (the browser side of the encryption).
    browser_key = ec.generate_private_key(ec.SECP256R1())
    p256dh = base64.urlsafe_b64encode(
        browser_key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    ).decode().rstrip("=")
    PushSubscription.objects.create(
        area=yaba, endpoint=f"http://127.0.0.1:{server.server_port}/push", p256dh=p256dh,
        auth=base64.urlsafe_b64encode(b"0123456789abcdef").decode().rstrip("="),
    )

    assert services.send_light_back_notifications(yaba.id) == 1
    assert received["auth"].startswith("vapid t=") and keys["VAPID_PUBLIC_KEY"] in received["auth"]
    assert len(received["body"]) > 50  # encrypted payload
    server.server_close()
