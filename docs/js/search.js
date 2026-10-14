import { store } from "./data.js";
import { isWatched } from "./collections.js";

export const norm = (s) => (s || "").toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f\u0640\u064b-\u065f]/g, "")
  .replace(/[أإآ]/g, "ا");

export function search(query, limit = Infinity) {
  const words = norm(query).split(/\s+/).filter(Boolean);
  if (!words.length) return store.movies;
  const out = [];
  for (let i = 0; i < store.movies.length && out.length < limit; i++) {
    const hay = store.index[i];
    if (words.every((w) => hay.includes(w))) out.push(store.movies[i]);
  }
  return out;
}

// Typing "Tom" suggests people first, then titles.
export function suggest(query) {
  const q = norm(query);
  if (q.length < 2) return { people: [], titles: [] };
  const seen = new Map();
  for (const m of store.movies) for (const p of [...m.a, ...m.d])
    if (norm(p).includes(q)) seen.set(p, (seen.get(p) || 0) + 1);
  const people = [...seen].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([name, n]) => ({ name, n }));
  return { people, titles: search(query, 6) };
}

export const filterAndSort = (list, f) => {
  let r = list.filter((m) =>
    (!f.type || f.type.includes(m.c)) &&
    (!f.genre || m.g.includes(f.genre)) &&
    (!f.quality || m.q === f.quality) && (!f.ramadan || m.rm) && (!f.country || m.co.includes(f.country)) && (!f.rated || m.rd === f.rated) &&
    (!f.era || (m.y && m.y >= f.era && m.y < f.era + 10)) &&
    (!f.minRating || (m.r || 0) >= f.minRating) &&
    (!f.watch || (f.watch === "seen") === isWatched(m.id)));
  const s = {
    rated: (a, b) => (b.r || 0) - (a.r || 0), votes: (a, b) => (b.v || 0) - (a.v || 0),
    new: (a, b) => (b.y || 0) - (a.y || 0), old: (a, b) => (a.y || 9999) - (b.y || 9999),
    az: (a, b) => a.t.localeCompare(b.t),
  }[f.sort];
  return s ? r.slice().sort(s) : r;
};
