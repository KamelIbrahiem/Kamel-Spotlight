// Personal data, saved on this device (localStorage): favorites, lists, watched, my ratings.
// Everything is stored by the title's STABLE KEY (m.k: IMDb id or title slug), never by row number,
// so data stays correct after the sheet is rebuilt. Shared online lists later = replace `backend`.
import { store } from "./data.js";

const KEY = "ks-collections-v2", ME = "ks-owner";
const read = () => ({ favorites: [], lists: [], watched: [], ratings: {}, ...JSON.parse(localStorage.getItem(KEY) || "{}") });
const write = (d) => localStorage.setItem(KEY, JSON.stringify(d));
const keyOf = (id) => store.movies[id]?.k;
const idOf = (k) => { if (!idOf.map || idOf.n !== store.movies.length) { idOf.map = new Map(store.movies.map((m) => [m.k, m.id])); idOf.n = store.movies.length; } return idOf.map.get(k); };
const toIds = (keys) => keys.map(idOf).filter((i) => i !== undefined);
export const idsFromKeys = toIds;
export const keysFromIds = (ids) => ids.map(keyOf).filter(Boolean);

export const owner = () => localStorage.getItem(ME) || "";
export const setOwner = (n) => localStorage.setItem(ME, n.trim());

const withList = (d, id) => d.lists.find((x) => x.id === id);
export const backend = {
  all: () => read().lists.map((l) => ({ ...l, ids: toIds(l.keys) })),
  create: (name, keys = []) => { const d = read(); const l = { id: Date.now().toString(36), name: name.trim(), owner: owner(), keys }; d.lists.push(l); write(d); return l; },
  toggle: (listId, movieId) => { const d = read(), l = withList(d, listId), k = keyOf(movieId); if (!l || !k) return; const i = l.keys.indexOf(k); i < 0 ? l.keys.push(k) : l.keys.splice(i, 1); write(d); },
  remove: (listId) => { const d = read(); d.lists = d.lists.filter((x) => x.id !== listId); write(d); },
};

const flag = (field) => ({
  list: () => toIds(read()[field]),
  has: (id) => read()[field].includes(keyOf(id)),
  toggle: (id) => { const d = read(), k = keyOf(id); if (!k) return false; const i = d[field].indexOf(k); i < 0 ? d[field].push(k) : d[field].splice(i, 1); write(d); return i < 0; },
});
const fav = flag("favorites"), seen = flag("watched");
export const favorites = fav.list, isFav = fav.has, toggleFav = fav.toggle;
export const watched = seen.list, isWatched = seen.has, toggleWatched = seen.toggle;

export const myRating = (id) => read().ratings[keyOf(id)] || 0;
export function setRating(id, n) { const d = read(), k = keyOf(id); if (!k) return; n ? (d.ratings[k] = n) : delete d.ratings[k]; write(d); }
export const rated = () => Object.entries(read().ratings).map(([k, v]) => [idOf(k), v]).filter(([i]) => i !== undefined);
