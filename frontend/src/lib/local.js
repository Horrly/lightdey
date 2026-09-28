// Per-browser data kept in localStorage: an anonymous device id, saved areas,
// the user's tariff band per area and their last report. Nothing here is personal.

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* storage full or blocked: features degrade gracefully */
  }
}

export function deviceId() {
  let id = read("ld.device", null);
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    write("ld.device", id);
  }
  return id;
}

export const myAreas = {
  list: () => read("ld.areas", []),
  has: (slug) => read("ld.areas", []).includes(slug),
  toggle(slug) {
    const list = read("ld.areas", []);
    const next = list.includes(slug) ? list.filter((s) => s !== slug) : [slug, ...list].slice(0, 12);
    write("ld.areas", next);
    return next.includes(slug);
  },
};

export const bands = {
  get: (slug) => read("ld.bands", {})[slug] || "",
  set(slug, band) {
    const all = read("ld.bands", {});
    if (band) all[slug] = band;
    else delete all[slug];
    write("ld.bands", all);
  },
};

export const lastReport = {
  get: (slug) => read("ld.last", {})[slug] || null,
  set(slug, state) {
    const all = read("ld.last", {});
    all[slug] = { state, at: new Date().toISOString() };
    write("ld.last", all);
  },
};

export const pushAreas = {
  has: (slug) => read("ld.push", []).includes(slug),
  set(slug, on) {
    const list = read("ld.push", []).filter((s) => s !== slug);
    write("ld.push", on ? [...list, slug] : list);
  },
};
