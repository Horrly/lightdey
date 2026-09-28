import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AreaRow, SectionTitle, Spinner, TONE } from "../components/ui";
import { api } from "../lib/api";
import { STATUS, timeAgo } from "../lib/format";
import { myAreas } from "../lib/local";
import { useNow, usePoll } from "../lib/usePoll";

function Search({ now }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults(null);
      return;
    }
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const data = await api(`/areas/?q=${encodeURIComponent(q)}`);
        if (!cancelled) setResults(data);
      } catch {
        if (!cancelled) setResults([]);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query]);

  return (
    <div>
      <input
        className="input py-4 text-base"
        placeholder="Search your area — e.g. Yaba, Bodija, Mayfair"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        aria-label="Search areas"
      />
      {results && (
        <div className="card mt-2 divide-y divide-night-700 p-1">
          {results.map((area) => (
            <AreaRow key={area.slug} area={area} now={now} />
          ))}
          <Link to={`/add?name=${encodeURIComponent(query.trim())}`} className="block px-3 py-3 text-sm text-glow-300 hover:underline">
            {results.length ? "Can't find your area?" : `No area called “${query.trim()}” yet.`} Add it →
          </Link>
        </div>
      )}
    </div>
  );
}

function MyAreas({ now }) {
  const slugs = myAreas.list();
  const { data } = usePoll(slugs.length ? `/areas/?slugs=${slugs.join(",")}` : null, 60000);
  if (!slugs.length) return null;
  const ordered = data ? slugs.map((s) => data.find((a) => a.slug === s)).filter(Boolean) : null;
  return (
    <>
      <SectionTitle>My areas</SectionTitle>
      <div className="card divide-y divide-night-700 p-1">
        {ordered ? ordered.map((area) => <AreaRow key={area.slug} area={area} now={now} />) : <Spinner />}
      </div>
    </>
  );
}

function Snapshot({ overview }) {
  const { totals } = overview;
  const reported = totals.on + totals.off;
  const pct = reported ? Math.round((totals.on / reported) * 100) : 0;
  return (
    <div className="card mt-6 p-5">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Right now across Nigeria</p>
      {reported === 0 ? (
        <p className="mt-2 text-sm text-slate-400">
          No reports in the last few hours. Be the first: search your area and tap <strong className="text-white">Light dey</strong> or{" "}
          <strong className="text-white">No light</strong>.
        </p>
      ) : (
        <>
          <p className="mt-2 text-2xl font-bold text-white">
            <span className="text-glow-400">{totals.on}</span> of {reported} reported areas have light
          </p>
          <div className="mt-3 flex h-2.5 overflow-hidden rounded-full bg-indigo-500/40" role="img" aria-label={`${pct}% of reported areas have light`}>
            <div className="bg-glow-400" style={{ width: `${pct}%` }} />
          </div>
          <p className="mt-2 text-xs text-slate-500">{overview.reports_today} reports today</p>
        </>
      )}
      {overview.cities.some((c) => c.on + c.off > 0) && (
        <div className="mt-4 flex flex-wrap gap-2">
          {overview.cities
            .filter((c) => c.on + c.off > 0)
            .slice(0, 8)
            .map((c) => (
              <span key={c.city} className="rounded-full bg-night-700 px-3 py-1 text-xs text-slate-300">
                {c.city}: <span className="text-glow-300">{c.on} 💡</span> · <span className="text-indigo-300">{c.off} 🌑</span>
              </span>
            ))}
        </div>
      )}
    </div>
  );
}

function Feed({ feed, now }) {
  if (!feed.length) return null;
  return (
    <>
      <SectionTitle>Live reports</SectionTitle>
      <ul className="card divide-y divide-night-700">
        {feed.map((item, i) => (
          <li key={`${item.slug}-${item.created_at}-${i}`}>
            <Link to={`/a/${item.slug}`} className="flex items-center gap-3 px-4 py-3 text-sm hover:bg-night-700/50">
              <span aria-hidden="true">{STATUS[item.state].emoji}</span>
              <span className="min-w-0 flex-1 truncate">
                <span className={TONE[item.state].text}>{STATUS[item.state].label}</span>
                <span className="text-slate-400"> · {item.area}</span>
              </span>
              <span className="shrink-0 text-xs text-slate-500">{timeAgo(item.created_at, now)}</span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

export default function Home() {
  const now = useNow();
  const { data: overview } = usePoll("/overview/", 60000);

  return (
    <>
      <section className="pt-2">
        <h1 className="text-4xl font-extrabold tracking-tight text-white">
          Light <span className="text-glow-400">dey?</span>
        </h1>
        <p className="mt-2 text-slate-400">
          See who has power right now, report yours in one tap, and get an alert when light comes back. No sign-up.
        </p>
        <div className="mt-5">
          <Search now={now} />
        </div>
      </section>

      <MyAreas now={now} />
      {overview ? (
        <>
          <Snapshot overview={overview} />
          <Feed feed={overview.feed} now={now} />
        </>
      ) : (
        <Spinner />
      )}
    </>
  );
}
