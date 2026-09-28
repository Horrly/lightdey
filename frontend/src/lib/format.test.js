import { describe, expect, it } from "vitest";
import { firstErrorMessage } from "./api";
import { duration, statusSentence, timeAgo, timelinePositions, weekday } from "./format";

const NOW = Date.parse("2026-09-28T12:00:00Z");

describe("duration", () => {
  it("formats minutes, hours and days", () => {
    expect(duration("2026-09-28T11:15:00Z", NOW)).toBe("45m");
    expect(duration("2026-09-28T09:45:00Z", NOW)).toBe("2h 15m");
    expect(duration("2026-09-25T08:00:00Z", NOW)).toBe("3d 4h");
    expect(duration("2026-09-28T13:00:00Z", NOW)).toBe("0m"); // clock skew never goes negative
  });
});

describe("timeAgo", () => {
  it("is human friendly", () => {
    expect(timeAgo("2026-09-28T11:59:30Z", NOW)).toBe("just now");
    expect(timeAgo("2026-09-28T11:30:00Z", NOW)).toBe("30m ago");
    expect(timeAgo("2026-09-28T07:00:00Z", NOW)).toBe("5h ago");
  });
});

describe("weekday", () => {
  it("parses dates as local days", () => {
    expect(weekday("2026-09-28")).toBe("Mon");
  });
});

describe("statusSentence", () => {
  it("builds a shareable line", () => {
    const area = { label: "Yaba, Lagos", status: "off", status_since: "2026-09-28T06:00:00Z" };
    expect(statusSentence(area, NOW)).toBe("🌑 No light for Yaba, Lagos — off for 6h 0m.");
    expect(statusSentence({ ...area, status: "unknown" }, NOW)).toBe("❔ No recent reports for Yaba, Lagos.");
  });
});

describe("timelinePositions", () => {
  it("clips segments to the window and converts to percentages", () => {
    const segs = [
      { state: "off", start: "2026-09-27T06:00:00Z", end: "2026-09-28T00:00:00Z" }, // starts before window
      { state: "on", start: "2026-09-28T00:00:00Z", end: "2026-09-28T12:00:00Z" },
    ];
    const [off, on] = timelinePositions(segs, NOW, 24);
    expect(off).toEqual({ state: "off", left: 0, width: 50 });
    expect(on).toEqual({ state: "on", left: 50, width: 50 });
  });
});

describe("firstErrorMessage", () => {
  it("reads DRF error shapes", () => {
    expect(firstErrorMessage({ detail: "Too many reports" })).toBe("Too many reports");
    expect(firstErrorMessage({ state: ['"x" is not a valid choice.'] })).toBe('state: "x" is not a valid choice.');
  });
});
