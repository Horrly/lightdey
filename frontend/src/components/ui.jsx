import { Link } from "react-router-dom";
import { STATUS, duration } from "../lib/format";

export const TONE = {
  on: { dot: "bg-glow-400", text: "text-glow-300", chip: "bg-glow-400/15 text-glow-300 ring-1 ring-glow-400/30" },
  off: { dot: "bg-indigo-400", text: "text-indigo-300", chip: "bg-indigo-500/15 text-indigo-200 ring-1 ring-indigo-400/30" },
  unknown: { dot: "bg-slate-500", text: "text-slate-400", chip: "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/30" },
};

export function StatusChip({ status }) {
  const meta = STATUS[status] ?? STATUS.unknown;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${TONE[status]?.chip ?? TONE.unknown.chip}`}>
      <span aria-hidden="true">{meta.emoji}</span>
      {meta.short}
    </span>
  );
}

export function AreaRow({ area, now }) {
  return (
    <Link
      to={`/a/${area.slug}`}
      className="flex items-center gap-3 rounded-xl px-3 py-3 transition hover:bg-night-700/60"
      data-testid="area-row"
    >
      <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${TONE[area.status]?.dot ?? TONE.unknown.dot}`} />
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium text-white">{area.name}</p>
        <p className="truncate text-xs text-slate-500">
          {area.city === area.state ? area.city : `${area.city}, ${area.state}`}
          {area.reports_last_hour > 0 && ` · ${area.reports_last_hour} report${area.reports_last_hour === 1 ? "" : "s"} this hour`}
        </p>
      </div>
      <div className="text-right">
        <StatusChip status={area.status} />
        {area.status !== "unknown" && area.status_since && (
          <p className="mt-1 text-[11px] text-slate-500">for {duration(area.status_since, now)}</p>
        )}
      </div>
    </Link>
  );
}

export function Spinner({ label = "Loading…" }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-night-600 border-t-glow-400" />
      {label}
    </div>
  );
}

export function SectionTitle({ children, action }) {
  return (
    <div className="mb-2 mt-8 flex items-center justify-between">
      <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-500">{children}</h2>
      {action}
    </div>
  );
}
