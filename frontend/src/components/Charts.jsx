import { BANDS, clock, timelinePositions, weekday } from "../lib/format";

const FILL = { on: "bg-glow-400", off: "bg-indigo-500/70", unknown: "bg-night-600" };

export function Timeline24h({ segments, now }) {
  const bars = timelinePositions(segments, now, 24);
  const ticks = [24, 18, 12, 6, 0];
  return (
    <div>
      <div className="relative h-9 overflow-hidden rounded-lg bg-night-700" role="img" aria-label="Power supply over the last 24 hours">
        {bars.map((b, i) => (
          <div key={i} className={`absolute inset-y-0 ${FILL[b.state]}`} style={{ left: `${b.left}%`, width: `${b.width}%` }} />
        ))}
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] text-slate-500">
        {ticks.map((h) => (
          <span key={h}>{h === 0 ? "now" : clock(new Date(now - h * 3600 * 1000).toISOString())}</span>
        ))}
      </div>
    </div>
  );
}

export function WeekChart({ days, band }) {
  const minimum = BANDS[band];
  return (
    <div>
      <div className="relative flex h-40 items-end gap-2">
        {minimum && (
          <div className="pointer-events-none absolute inset-x-0 border-t border-dashed border-rose-400/70" style={{ bottom: `${(minimum / 24) * 100}%` }}>
            <span className="absolute -top-5 left-0 rounded bg-night-900/80 px-1 text-[10px] font-medium text-rose-300">
              Band {band} minimum · {minimum}h
            </span>
          </div>
        )}
        {days.map((d) => (
          <div key={d.date} className="flex h-full flex-1 flex-col justify-end" title={`${d.on}h light, ${d.off}h no light, ${d.unknown}h unreported`}>
            <div className="flex h-full flex-col justify-end overflow-hidden rounded-md bg-night-700">
              <div className="bg-glow-400" style={{ height: `${(d.on / 24) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
      <div className="mt-1.5 flex gap-2">
        {days.map((d) => (
          <span key={d.date} className={`flex-1 text-center text-[11px] ${d.is_today ? "font-semibold text-white" : "text-slate-500"}`}>
            {d.is_today ? "Today" : weekday(d.date)}
            <span className="block font-semibold text-glow-300">{d.on > 0 ? `${d.on}h` : "–"}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

export function Legend() {
  return (
    <p className="mt-3 flex flex-wrap gap-4 text-xs text-slate-400">
      <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm bg-glow-400" /> Light</span>
      <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm bg-indigo-500/70" /> No light</span>
      <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm bg-night-600" /> No reports</span>
    </p>
  );
}
