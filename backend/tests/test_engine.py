from datetime import datetime, timedelta, timezone as dt_tz

import pytest
from django.utils import timezone

from power.engine import OFF, ON, UNKNOWN, band_check, build_timeline, current_status, daily_hours

LAGOS = dt_tz(timedelta(hours=1))
T0 = datetime(2026, 9, 28, 8, 0, tzinfo=LAGOS)


def at(minutes):
    return T0 + timedelta(minutes=minutes)


def states(segments):
    return [(s.state, round((s.end - s.start).total_seconds() / 60)) for s in segments]


def test_no_reports_is_unknown():
    assert states(build_timeline([], at(0), at(60))) == [(UNKNOWN, 60)]


def test_state_carries_forward_until_stale():
    segments = build_timeline([(at(5), ON)], at(0), at(6 * 60))
    # On from the report's bucket (08:00) until 4h after the report itself (12:05),
    # which rounds to the end of that bucket (12:10). Then unknown.
    assert states(segments) == [(ON, 250), (UNKNOWN, 110)]


def test_switches_on_contrary_report():
    segments = build_timeline([(at(1), ON), (at(95), OFF), (at(185), ON)], at(0), at(240))
    assert states(segments) == [(ON, 90), (OFF, 90), (ON, 60)]


def test_majority_wins_within_a_bucket_and_ties_keep_previous():
    reports = [(at(1), ON), (at(12), OFF), (at(13), OFF), (at(14), ON), (at(25), ON), (at(26), OFF)]
    # bucket 0: on | bucket 10: 2 off vs 1 on -> off | bucket 20: tie -> stays off
    assert states(build_timeline(reports, at(0), at(30))) == [(ON, 10), (OFF, 20)]


def test_history_before_the_window_sets_the_starting_state():
    segments = build_timeline([(at(-60), OFF)], at(0), at(60))
    assert states(segments) == [(OFF, 60)]


def test_current_status_and_since():
    reports = [(at(1), OFF), (at(125), ON), (at(128), ON)]
    segments = build_timeline(reports, at(0), at(180))
    # Without reports we only know the bucket; with them, the exact first report.
    assert current_status(segments, at(180)) == (ON, at(120))
    assert current_status(segments, at(180), reports) == (ON, at(125))
    assert current_status([], at(0)) == (UNKNOWN, None)


def test_daily_hours_split_by_lagos_day(settings):
    settings.TIME_ZONE = "Africa/Lagos"
    timezone.activate("Africa/Lagos")
    day1 = datetime(2026, 9, 27, 0, 0, tzinfo=LAGOS)
    reports = [(day1 + timedelta(hours=1), ON), (day1 + timedelta(hours=4), ON),  # on 01:00 -> 08:00 (stale)
               (day1 + timedelta(hours=20), OFF), (day1 + timedelta(hours=23), OFF)]  # off 20:00 -> 03:00 next day
    now = day1 + timedelta(days=1, hours=10)
    segments = build_timeline(reports, day1, now)
    days = daily_hours(segments, 2, now)

    assert [d["date"] for d in days] == ["2026-09-27", "2026-09-28"]
    assert days[0]["on"] == 7.0 and days[0]["off"] == 4.0 and days[0]["is_today"] is False
    assert days[1]["off"] == 3.0 and days[1]["on"] == 0 and days[1]["is_today"] is True
    assert days[0]["on"] + days[0]["off"] + days[0]["unknown"] == 24.0


@pytest.mark.parametrize(
    "band, expected",
    [("A", (20, 2, 2, 11.0)), ("C", (12, 2, 1, 11.0)), ("e", (4, 2, 0, 11.0))],
)
def test_band_check(band, expected):
    days = [
        {"on": 10.0, "off": 12.0, "is_today": False},
        {"on": 12.0, "off": 10.0, "is_today": False},
        {"on": 2.0, "off": 1.0, "is_today": False},  # too few reports to judge
        {"on": 1.0, "off": 1.0, "is_today": True},  # today is never judged
    ]
    result = band_check(days, band)
    assert (result["minimum"], result["days_judged"], result["days_below"], result["average"]) == expected


def test_band_check_ignores_unknown_bands():
    assert band_check([], None) is None
    assert band_check([], "Z") is None
