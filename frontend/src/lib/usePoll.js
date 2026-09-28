import { useCallback, useEffect, useState } from "react";
import { api } from "./api";

/** Fetch `path` now and every `intervalMs` while the tab is visible. */
export function usePoll(path, intervalMs = 60000) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!path) return;
    try {
      setData(await api(path));
      setError(null);
    } catch (err) {
      setError(err);
    }
  }, [path]);

  useEffect(() => {
    setData(null);
    load();
    const timer = setInterval(() => document.visibilityState === "visible" && load(), intervalMs);
    const onVisible = () => document.visibilityState === "visible" && load();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [load, intervalMs]);

  return { data, error, reload: load, setData };
}

/** Re-render every `ms` so "for 2h 15m" keeps counting. */
export function useNow(ms = 30000) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), ms);
    return () => clearInterval(t);
  }, [ms]);
  return now;
}
