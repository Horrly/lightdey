import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";

const STATES = [
  "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno", "Cross River", "Delta",
  "Ebonyi", "Edo", "Ekiti", "Enugu", "FCT", "Gombe", "Imo", "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi",
  "Kogi", "Kwara", "Lagos", "Nasarawa", "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto",
  "Taraba", "Yobe", "Zamfara",
];

export default function AddArea() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: params.get("name") || "", city: "", state: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const area = await api("/areas/", { method: "POST", body: form });
      navigate(`/a/${area.slug}`, { replace: true });
    } catch (err) {
      setError({ text: err.message, slug: err.data?.slug });
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <Link to="/" className="text-sm text-slate-400 hover:text-white">
        ← Back
      </Link>
      <h1 className="mt-2 text-2xl font-bold text-white">Add your area</h1>
      <p className="mt-1 text-sm text-slate-400">Use the name people around you actually call it, like “Mayfair” or “Gwarinpa”.</p>

      <form onSubmit={submit} className="card mt-6 space-y-4 p-5">
        <label className="block">
          <span className="text-sm font-medium text-slate-300">Area / neighbourhood</span>
          <input className="input mt-1" value={form.name} onChange={set("name")} required maxLength={80} />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-300">City or town</span>
          <input className="input mt-1" value={form.city} onChange={set("city")} required maxLength={60} />
        </label>
        <label className="block">
          <span className="text-sm font-medium text-slate-300">State</span>
          <select className="input mt-1" value={form.state} onChange={set("state")} required>
            <option value="" disabled>
              Choose a state
            </option>
            {STATES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        {error && (
          <p className="rounded-xl bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
            {error.text}{" "}
            {error.slug && (
              <Link className="font-semibold underline" to={`/a/${error.slug}`}>
                Open it
              </Link>
            )}
          </p>
        )}
        <button className="btn w-full bg-glow-400 py-3 text-night-950 hover:bg-glow-300" disabled={busy}>
          {busy ? "Adding…" : "Add area"}
        </button>
      </form>
    </div>
  );
}
