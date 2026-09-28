"""Turn scattered "light dey / no light" reports into a supply timeline.

Model
-----
Time is split into 10-minute buckets. A bucket with reports takes the majority
state of those reports (a tie keeps whatever came before). A bucket without
reports carries the previous state forward, but only for STALE_AFTER since the
last report; after that we honestly say "unknown" instead of guessing.

From the timeline we derive:
- the current status and how long it has lasted ("No light for 6h 20m")
- hours of supply per day, which we compare with NERC's band minimums

These are pure functions over (timestamp, state) pairs, so they're easy to test.
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.utils import timezone

BUCKET = timedelta(minutes=10)
STALE_AFTER = timedelta(hours=4)

ON, OFF, UNKNOWN = "on", "off", "unknown"

# NERC Service-Based Tariff: minimum daily hours of supply per band.
BAND_MIN_HOURS = {"A": 20, "B": 16, "C": 12, "D": 8, "E": 4}


@dataclass
class Segment:
    start: datetime
    end: datetime
    state: str

    @property
    def hours(self):
        return (self.end - self.start).total_seconds() / 3600

    def as_dict(self):
        return {"start": self.start, "end": self.end, "state": self.state}


def _floor(dt):
    """Round down to the start of its bucket."""
    seconds = int(BUCKET.total_seconds())
    return datetime.fromtimestamp(int(dt.timestamp()) // seconds * seconds, tz=dt.tzinfo)


def build_timeline(reports, start, end):
    """Return merged Segments covering [start, end).

    `reports` is an iterable of (created_at, state) and should include reports
    from up to STALE_AFTER before `start`, so the first bucket knows its history.
    """
    reports = sorted(reports, key=lambda r: r[0])
    if end <= start:
        return []

    segments = []
    state, last_report_at = UNKNOWN, None
    i = 0
    cursor = _floor(start)

    def push(seg_start, seg_end, seg_state):
        seg_start, seg_end = max(seg_start, start), min(seg_end, end)
        if seg_end <= seg_start:
            return
        if segments and segments[-1].state == seg_state and segments[-1].end == seg_start:
            segments[-1].end = seg_end
        else:
            segments.append(Segment(seg_start, seg_end, seg_state))

    # Replay everything before the first bucket to get the starting state.
    while i < len(reports) and reports[i][0] < cursor:
        state, last_report_at = reports[i][1], reports[i][0]
        i += 1

    while cursor < end:
        bucket_end = cursor + BUCKET
        on = off = 0
        while i < len(reports) and reports[i][0] < bucket_end:
            if reports[i][1] == ON:
                on += 1
            else:
                off += 1
            last_report_at = reports[i][0]
            i += 1

        if on or off:
            if on != off:
                state = ON if on > off else OFF
            # tie: keep the previous state
        elif last_report_at is None or cursor - last_report_at >= STALE_AFTER:
            state = UNKNOWN

        push(cursor, bucket_end, state)
        cursor = bucket_end

    return segments


def current_status(segments, now, reports=()):
    """(state, since) from a timeline that ends at `now`.

    Segments start on bucket boundaries, so when the reports are given we use the
    first report that started the current state instead: "off since 21:08", not 21:00.
    """
    if not segments:
        return UNKNOWN, None
    last = segments[-1]
    if last.state == UNKNOWN:
        return last.state, last.start
    first = min((at for at, state in reports if at >= last.start and state == last.state), default=None)
    return last.state, first or last.start


def daily_hours(segments, days, now):
    """Hours on/off/unknown for each of the last `days` local days (oldest first).

    Today only counts up to `now`, so its numbers are "so far".
    """
    tz = timezone.get_current_timezone()
    today = timezone.localtime(now, tz).date()
    result = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        day_start = datetime.combine(day, time.min, tzinfo=tz)
        day_end = min(day_start + timedelta(days=1), now)
        totals = {ON: 0.0, OFF: 0.0, UNKNOWN: 0.0}
        for seg in segments:
            overlap = (min(seg.end, day_end) - max(seg.start, day_start)).total_seconds()
            if overlap > 0:
                totals[seg.state] += overlap / 3600
        result.append({
            "date": day.isoformat(),
            "on": round(totals[ON], 1),
            "off": round(totals[OFF], 1),
            "unknown": round(totals[UNKNOWN], 1),
            "is_today": day == today,
        })
    return result


def band_check(days, band):
    """Compare completed days with a band's minimum. Returns None for unknown bands."""
    minimum = BAND_MIN_HOURS.get((band or "").upper())
    if minimum is None:
        return None
    complete = [d for d in days if not d["is_today"]]
    reported = [d for d in complete if d["on"] + d["off"] >= 12]  # enough reports to judge
    if not reported:
        return {"band": band.upper(), "minimum": minimum, "days_judged": 0, "days_below": 0, "average": None}
    below = [d for d in reported if d["on"] < minimum]
    return {
        "band": band.upper(),
        "minimum": minimum,
        "days_judged": len(reported),
        "days_below": len(below),
        "average": round(sum(d["on"] for d in reported) / len(reported), 1),
    }
