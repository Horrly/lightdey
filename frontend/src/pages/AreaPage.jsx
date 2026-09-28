import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Legend, Timeline24h, WeekChart } from "../components/Charts";
import { SectionTitle, Spinner, TONE } from "../components/ui";
import { api } from "../lib/api";
import { BANDS, STATUS, clock, duration, statusSentence, timeAgo } from "../lib/format";
import { bands, lastReport, myAreas, pushAreas } from "../lib/local";
import { disableLightAlerts, enableLightAlerts, needsInstallForPush, pushSupported } from "../lib/push";
import { useNow, usePoll } from "../lib/usePoll";

const PANEL = {
  on: "border-glow-400/40 bg-gradient-to-b from-glow-400/20 to-night-800 glow",
  off: "border-indigo-400/30 bg-gradient-to-b from-indigo-600/20 to-night-800",
  unknown: "border-night-600 bg-night-800",
};

function StatusPanel({ area, now }) {
  const meta = STATUS[area.status];
  const { on, off } = area.last_hour;
  return (
    <div className={`rounded-3xl border p-6 text-center ${PANEL[area.status]}`} data-testid="status-panel">
      <div className="text-6xl" aria-hidden="true">{meta.emoji}</div>
      <p className={`mt-3 text-3xl font-extrabold ${area.status === "unknown" ? "text-slate-300" : "text-white"}`}>{meta.label}</p>
      {area.status !== "unknown" && area.status_since && (
        <p className={`mt-1 text-lg font-medium ${TONE[area.status].text}`}>
          {area.status === "on" ? "on" : "off"} for {duration(area.status_since, now)}
          <span className="text-sm text-slate-400"> · since {clock(area.status_since)}</span>
        </p>
      )}
      <p className="mt-3 text-xs text-slate-400">
        {on + off > 0
          ? `Last hour: ${on} said light dey, ${off} said no light`
          : area.last_report_at
            ? `Last report ${timeAgo(area.last_report_at, now)}`
            : "No one has reported here yet — be the first."}
      </p>
    </div>
  );
}

function ReportButtons({ slug, onReported }) {
  const [busy, setBusy] = useState(null);
  const [message, setMessage] = useState(null);
  const mine = lastReport.get(slug);
  const recentMine = mine && Date.now() - new Date(mine.at) < 10 * 60 * 1000 ? mine.state : null;

  async function send(state) {
    setBusy(state);
    setMessage(null);
    try {
      const res = await api(`/areas/${slug}/reports/`, { method: "POST", body: { state } });
      lastReport.set(slug, state);
      setMessage({ ok: true, text: res.created ? "Thanks! Your report is live for everyone." : "Updated your report." });
      onReported(res.area);
    } catch (err) {
      setMessage({ ok: false, text: err.message });
    } finally {
      setBusy(null);
    }
  }

  const base = "btn flex-1 flex-col gap-1 rounded-2xl py-5 text-base";
  return (
    <div className="mt-4">
      <p className="mb-2 text-center text-sm text-slate-400">What's happening at your place right now?</p>
      <div className="flex gap-3">
        <button
          className={`${base} bg-glow-400 text-night-950 hover:bg-glow-300 ${recentMine === "on" ? "ring-4 ring-glow-300/40" : ""}`}
          onClick={() => send("on")}
          disabled={Boolean(busy)}
        >
          <span className="text-2xl" aria-hidden="true">💡</span>
          {busy === "on" ? "Sending…" : "Light dey"}
        </button>
        <button
          className={`${base} bg-indigo-600 text-white hover:bg-indigo-500 ${recentMine === "off" ? "ring-4 ring-indigo-400/40" : ""}`}
          onClick={() => send("off")}
          disabled={Boolean(busy)}
        >
          <span className="text-2xl" aria-hidden="true">🌑</span>
          {busy === "off" ? "Sending…" : "No light"}
        </button>
      </div>
      {message && (
        <p role="status" className={`mt-3 text-center text-sm ${message.ok ? "text-emerald-300" : "text-rose-300"}`}>
          {message.text}
        </p>
      )}
    </div>
  );
}

function Actions({ area }) {
  const [saved, setSaved] = useState(() => myAreas.has(area.slug));
  const [alerts, setAlerts] = useState(() => pushAreas.has(area.slug));
  const [note, setNote] = useState("");
  const shareUrl = `${window.location.origin}/a/${area.slug}`;
  const shareText = `${statusSentence(area)} Check or report on LightDey:`;

  async function toggleAlerts() {
    setNote("");
    try {
      if (alerts) {
        await disableLightAlerts(area.slug);
        setAlerts(false);
      } else {
        await enableLightAlerts(area.slug);
        setAlerts(true);
        setNote("We'll notify you when light comes back here.");
      }
    } catch (err) {
      setNote(err.message);
    }
  }

  async function share() {
    if (navigator.share) {
      try {
        await navigator.share({ title: `Light dey for ${area.name}?`, text: shareText, url: shareUrl });
        return;
      } catch {
        /* cancelled: fall back to WhatsApp link */
      }
    }
    window.open(`https://wa.me/?text=${encodeURIComponent(`${shareText} ${shareUrl}`)}`, "_blank", "noopener");
  }

  const showAlerts = area.push_enabled && (pushSupported() || needsInstallForPush());

  return (
    <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-3">
      <button className="btn-ghost" onClick={() => setSaved(myAreas.toggle(area.slug))}>
        {saved ? "★ Saved" : "☆ Save area"}
      </button>
      <button className="btn-ghost" onClick={share}>
        ↗ Share
      </button>
      {showAlerts && (
        <button
          className={`btn-ghost col-span-2 sm:col-span-1 ${alerts ? "border-glow-400/50 text-glow-300" : ""}`}
          onClick={needsInstallForPush() ? () => setNote("On iPhone: tap Share → Add to Home Screen, open LightDey from there, then turn on alerts.") : toggleAlerts}
        >
          {alerts ? "🔔 Alerts on" : "🔕 Alert me when light returns"}
        </button>
      )}
      {note && <p className="col-span-full text-center text-sm text-slate-300">{note}</p>}
    </div>
  );
}

function BandSection({ area, band, setBand }) {
  const check = area.band_check;
  return (
    <>
      <SectionTitle
        action={
          <label className="flex items-center gap-2 text-xs text-slate-400">
            My band
            <select
              value={band}
              onChange={(e) => setBand(e.target.value)}
              className="rounded-lg border border-night-600 bg-night-900 px-2 py-1 text-xs text-white"
              aria-label="Your tariff band"
            >
              <option value="">Not sure</option>
              {Object.entries(BANDS).map(([b, h]) => (
                <option key={b} value={b}>
                  Band {b} ({h}h+)
                </option>
              ))}
            </select>
          </label>
        }
      >
        Hours of light this week
      </SectionTitle>
      <div className="card p-4">
        <WeekChart days={area.daily} band={band} />
        {check && check.days_judged > 0 && (
          <p className={`mt-4 rounded-xl px-3 py-2 text-sm ${check.days_below ? "bg-rose-500/10 text-rose-200" : "bg-emerald-500/10 text-emerald-200"}`}>
            {check.days_below
              ? `Band ${check.band} should get at least ${check.minimum}h a day. Reports here averaged ${check.average}h, below the minimum on ${check.days_below} of ${check.days_judged} days.`
              : `Reports here averaged ${check.average}h a day, meeting the Band ${check.band} minimum of ${check.minimum}h.`}
          </p>
        )}
        {check && check.days_judged === 0 && (
          <p className="mt-4 text-xs text-slate-500">Not enough reports yet to compare with Band {check.band}. The more people report, the clearer this gets.</p>
        )}
        {!band && <p className="mt-4 text-xs text-slate-500">Pick your band (it's on your electricity bill) to compare supply with what you pay for.</p>}
        <p className="mt-2 text-[11px] text-slate-500">Estimated from crowd reports. Days with fewer than 12 reported hours aren't judged.</p>
      </div>
    </>
  );
}

export default function AreaPage() {
  const { slug } = useParams();
  const now = useNow();
  const [band, setBandState] = useState(() => bands.get(slug));
  const { data: area, error, reload } = usePoll(`/areas/${slug}/${band ? `?band=${band}` : ""}`, 60000);

  useEffect(() => setBandState(bands.get(slug)), [slug]);

  function setBand(value) {
    bands.set(slug, value);
    setBandState(value);
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <p className="text-4xl">🔎</p>
        <p className="mt-3 font-semibold text-white">Area not found</p>
        <Link to="/" className="mt-3 inline-block text-sm text-glow-300 hover:underline">
          Search for your area
        </Link>
      </div>
    );
  }
  if (!area) return <Spinner />;

  return (
    <>
      <Link to="/" className="text-sm text-slate-400 hover:text-white">
        ← All areas
      </Link>
      <h1 className="mb-4 mt-2 text-2xl font-bold text-white">
        {area.name}
        <span className="block text-sm font-normal text-slate-400">
          {area.city === area.state ? area.city : `${area.city}, ${area.state}`}
        </span>
      </h1>

      <StatusPanel area={area} now={now} />
      <ReportButtons slug={slug} onReported={reload} />
      <Actions area={area} />

      <SectionTitle>Last 24 hours</SectionTitle>
      <div className="card p-4">
        <Timeline24h segments={area.timeline} now={now} />
        <Legend />
      </div>

      <BandSection area={area} band={band} setBand={setBand} />

      {area.recent_reports.length > 0 && (
        <>
          <SectionTitle>Recent reports</SectionTitle>
          <ul className="card divide-y divide-night-700 text-sm">
            {area.recent_reports.map((r, i) => (
              <li key={i} className="flex items-center justify-between px-4 py-2.5">
                <span className={TONE[r.state].text}>
                  {STATUS[r.state].emoji} {STATUS[r.state].label}
                </span>
                <span className="text-xs text-slate-500">
                  {clock(r.created_at)} · {timeAgo(r.created_at, now)}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
