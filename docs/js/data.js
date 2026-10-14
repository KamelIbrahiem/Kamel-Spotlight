import { CONFIG } from "./config.js";

const cache = {};
const get = (name) => cache[name] ??= fetch(`${CONFIG.dataPath}/${name}.json`, { cache: "no-cache" }).then((r) => {
  if (!r.ok) throw new Error(name); return r.json();
});

export const store = { movies: [], index: [] };
export async function loadCore() {
  [store.movies, store.index] = await Promise.all([get("movies"), get("search-index")]);
}
export const loadStats = () => get("statistics");
export const loadHealth = () => get("health");
export const loadPeople = () => get("people");
export async function loadDetails(id) {          // lazy chunks of 250 titles
  const chunk = await get(`details/${Math.floor(id / 250)}`);
  return chunk[id];
}
export const loadCollections = () => get("collections");
