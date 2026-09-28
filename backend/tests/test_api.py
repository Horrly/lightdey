from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from power import services
from power.models import Area, Report

pytestmark = pytest.mark.django_db


class TestAreas:
    def test_search(self, api, yaba):
        Area.objects.create(name="Bodija", city="Ibadan", state="Oyo")
        assert [a["label"] for a in api.get("/api/areas/?q=yab").data] == ["Yaba, Lagos"]
        assert [a["label"] for a in api.get("/api/areas/?q=oyo").data] == ["Bodija, Ibadan"]
        assert len(api.get("/api/areas/?slugs=yaba-lagos,nope").data) == 1

    def test_recently_reported_areas_come_first(self, api, report, yaba):
        Area.objects.create(name="Akoka", city="Lagos", state="Lagos")
        report(yaba, "on")
        assert [a["name"] for a in api.get("/api/areas/").data] == ["Yaba", "Akoka"]

    def test_add_area_normalises_and_dedupes(self, api):
        res = api.post("/api/areas/", {"name": "  ogba  ", "city": "lagos", "state": "Lagos"}, format="json")
        assert res.status_code == 201
        assert res.data["label"] == "Ogba, Lagos" and res.data["slug"] == "ogba-lagos"

        dup = api.post("/api/areas/", {"name": "OGBA", "city": "Lagos", "state": "Lagos"}, format="json")
        assert dup.status_code == 409 and dup.data["slug"] == "ogba-lagos"

    def test_add_area_validates_state(self, api):
        res = api.post("/api/areas/", {"name": "X", "city": "Y", "state": "Wakanda"}, format="json")
        assert res.status_code == 400

    def test_add_area_is_rate_limited_per_device(self, make_client):
        client = make_client("device-aaaaaaaa")
        for i in range(3):
            assert client.post("/api/areas/", {"name": f"Area {i}", "city": "Ife", "state": "Osun"},
                               format="json").status_code == 201
        res = client.post("/api/areas/", {"name": "Area 4", "city": "Ife", "state": "Osun"}, format="json")
        assert res.status_code == 429

    def test_requires_device_id(self, yaba):
        from rest_framework.test import APIClient
        res = APIClient().post(f"/api/areas/{yaba.slug}/reports/", {"state": "on"}, format="json")
        assert res.status_code == 400


class TestReports:
    def test_report_updates_status(self, report, yaba, api):
        res = report(yaba, "off")
        assert res.status_code == 201
        assert res.data["area"]["status"] == "off"
        assert res.data["area"]["reports_last_hour"] == 1

        detail = api.get(f"/api/areas/{yaba.slug}/").data
        assert detail["status"] == "off"
        assert detail["last_hour"] == {"on": 0, "off": 1}
        assert detail["recent_reports"][0]["state"] == "off"
        assert "device_hash" not in detail["recent_reports"][0]

    def test_same_device_corrects_instead_of_spamming(self, report, yaba):
        report(yaba, "off")
        res = report(yaba, "on")
        assert res.status_code == 200 and res.data["created"] is False
        assert Report.objects.count() == 1
        assert res.data["area"]["status"] == "on"

    def test_majority_of_different_people(self, report, yaba, make_client):
        report(yaba, "on", client=make_client())
        report(yaba, "off", client=make_client())
        report(yaba, "off", client=make_client())
        yaba.refresh_from_db()
        assert yaba.status == "off"

    def test_device_area_limit(self, make_client):
        client = make_client("device-bbbbbbbb")
        areas = [Area.objects.create(name=f"A{i}", city="Lagos", state="Lagos") for i in range(6)]
        for area in areas[:5]:
            assert client.post(f"/api/areas/{area.slug}/reports/", {"state": "on"}, format="json").status_code == 201
        res = client.post(f"/api/areas/{areas[5].slug}/reports/", {"state": "on"}, format="json")
        assert res.status_code == 429

    def test_ip_limit(self, yaba, make_client):
        Report.objects.bulk_create([
            Report(area=yaba, state="on", created_at=timezone.now(), device_hash=str(i),
                   ip_hash=services.fingerprint("10.9.9.9"))
            for i in range(services.MAX_REPORTS_PER_IP_PER_HOUR)
        ])
        res = make_client(ip="10.9.9.9").post(f"/api/areas/{yaba.slug}/reports/", {"state": "on"}, format="json")
        assert res.status_code == 429

    def test_stale_status_becomes_unknown(self, api, yaba):
        long_ago = timezone.now() - timedelta(hours=5)
        Report.objects.create(area=yaba, state="on", created_at=long_ago, device_hash="x", ip_hash="y")
        services.refresh_status(yaba, now=long_ago + timedelta(minutes=5))

        data = api.get("/api/areas/?q=yaba").data[0]
        assert data["status"] == "unknown"


class TestDetailAndOverview:
    def test_detail_includes_history_and_band_check(self, api, report, yaba):
        report(yaba, "on")
        data = api.get(f"/api/areas/{yaba.slug}/?band=A&days=7").data
        assert len(data["daily"]) == 7 and data["daily"][-1]["is_today"] is True
        assert data["timeline"][-1]["state"] == "on"
        assert data["band_check"]["minimum"] == 20
        assert data["push_enabled"] is False

    def test_overview(self, api, report, yaba, make_client):
        ikeja = Area.objects.create(name="Ikeja", city="Lagos", state="Lagos")
        Area.objects.create(name="Bodija", city="Ibadan", state="Oyo")
        report(yaba, "on")
        report(ikeja, "off", client=make_client())

        data = api.get("/api/overview/").data
        assert data["totals"] == {"on": 1, "off": 1, "unknown": 1}
        lagos = data["cities"][0]
        assert (lagos["city"], lagos["on"], lagos["off"]) == ("Lagos", 1, 1)
        assert [f["area"] for f in data["feed"]] == ["Ikeja, Lagos", "Yaba, Lagos"]
        assert data["reports_today"] == 2


class TestCommands:
    def test_seed_areas_is_idempotent_and_creates_no_reports(self):
        call_command("seed_areas")
        count = Area.objects.count()
        call_command("seed_areas")
        assert Area.objects.count() == count > 50
        assert Report.objects.count() == 0

    def test_simulator_refuses_in_production(self, settings):
        settings.DEBUG = False
        from django.core.management.base import CommandError
        with pytest.raises(CommandError):
            call_command("simulate_reports")


class TestSharePreviews:
    @pytest.fixture
    def built(self, settings, tmp_path):
        (tmp_path / "index.html").write_text(
            "<html><head><title>LightDey</title><!--SHARE_META--></head><body><div id='root'></div></body></html>"
        )
        settings.FRONTEND_DIST = tmp_path
        settings.SITE_URL = "https://lightdey.example"

    def test_area_page_has_live_status_in_preview(self, client, built, report, yaba):
        report(yaba, "off")
        html = client.get("/a/yaba-lagos").content.decode()
        assert "<title>Is there light in Yaba, Lagos? — LightDey</title>" in html
        assert "🌑 No light — off for" in html
        assert 'og:url" content="https://lightdey.example/a/yaba-lagos"' in html

    def test_other_pages_get_default_preview(self, client, built):
        html = client.get("/").content.decode()
        assert "Is there light in your area?" in html

    def test_health(self, client):
        assert client.get("/api/health/").json() == {"status": "ok"}


def test_duplicate_area_race_returns_conflict(api, monkeypatch):
    """If two people add the same area at once, the loser gets a 409, not a crash."""
    Area.objects.create(name="Ogba", city="Lagos", state="Lagos")
    # Simulate the race: the pre-check misses the existing row.
    from power import views
    real_filter = Area.objects.filter
    calls = {"n": 0}

    def flaky_filter(*args, **kwargs):
        calls["n"] += 1
        return Area.objects.none() if calls["n"] == 1 else real_filter(*args, **kwargs)

    monkeypatch.setattr(views.Area.objects, "filter", flaky_filter)
    res = api.post("/api/areas/", {"name": "Ogba", "city": "Lagos", "state": "Lagos"}, format="json")
    assert res.status_code == 409 and res.data["slug"] == "ogba-lagos"
