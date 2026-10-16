import { CONFIG } from "./config.js";

const cache = {};
const get = (name) => cache[name] ??= fetch(`${CONFIG.dataPath}/${name}.json`, { cache: "no-cache" }).then((r) => {
  if (!r.ok) throw new Error(name); return r.json();
});

export const store = { movies: [], index: [] };
export async function loadCore() { store.movies = await get("movies"); }       // the 6.8 MB search index loads only when someone searches
export const ensureIndex = async () => { if (!store.index.length) store.index = await get("search-index"); };
export const loadStats = () => get("statistics");
export const loadHealth = () => get("health");
export const loadPeople = () => get("people");
export async function loadDetails(id) {          // lazy chunks of 250 titles
  const chunk = await get(`details/${Math.floor(id / 250)}`);
  return chunk[id];
}
export const loadCollections = () => get("collections");
