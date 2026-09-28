export const STATUS = {
  on: { label: "Light dey", emoji: "💡", short: "Light", tone: "on" },
  off: { label: "No light", emoji: "🌑", short: "No light", tone: "off" },
  unknown: { label: "No recent reports", emoji: "❔", short: "Unknown", tone: "unknown" },
};

// "2h 15m", "45m", "3d 4h"
export function duration(fromIso, now = Date.now()) {
  const minutes = Math.max(0, Math.floor((now - new Date(fromIso)) / 60000));
  const hours = Math.floor(minutes / 60);
  if (hours >= 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`;
  if (hours > 0) return `${hours}h ${minutes % 60}m`;
  return `${minutes}m`;
}

export function timeAgo(iso, now = Date.now()) {
  const seconds = Math.max(0, Math.floor((now - new Date(iso)) / 1000));
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function clock(iso) {
  return new Date(iso).toLocaleTimeString("en-NG", { hour: "numeric", minute: "2-digit" });
}

export function weekday(isoDate) {
  // "2026-09-28" -> "Mon"; parse as a local date, not UTC
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-NG", { weekday: "short" });
}

// One-line status summary, e.g. for sharing.
export function statusSentence(area, now = Date.now()) {
  if (area.status === "on") return `💡 Light dey for ${area.label}${area.status_since ? ` — on for ${duration(area.status_since, now)}` : ""}.`;
  if (area.status === "off") return `🌑 No light for ${area.label}${area.status_since ? ` — off for ${duration(area.status_since, now)}` : ""}.`;
  return `❔ No recent reports for ${area.label}.`;
}

// Place timeline segments on a 0–100% scale for the last `hours` hours.
export function timelinePositions(segments, now = Date.now(), hours = 24) {
  const start = now - hours * 3600 * 1000;
  const span = now - start;
  return segments
    .map((s) => {
      const a = Math.max(new Date(s.start).getTime(), start);
      const b = Math.min(new Date(s.end).getTime(), now);
      return { state: s.state, left: ((a - start) / span) * 100, width: ((b - a) / span) * 100 };
    })
    .filter((s) => s.width > 0);
}

export const BANDS = { A: 20, B: 16, C: 12, D: 8, E: 4 };
