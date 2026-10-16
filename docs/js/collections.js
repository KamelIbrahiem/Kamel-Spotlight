// Personal data, saved on this device (localStorage): favorites, lists, watched, my ratings.
// Everything is stored by the title's STABLE KEY (m.k: IMDb id or title slug), never by row number,
// so data stays correct after the sheet is rebuilt. Shared online lists later = replace `backend`.
import { store } from "./data.js";

const KEY = "ks-collections-v2", ME = "ks-owner";
// Keys of titles whose name was repaired (old garbled key -> corrected key), so saved data follows the title.
const FIXED = { "t:ابتسامة في عيون حزينة:1980": "t:ابتسامة في عيون حزينة:1987", "t:المليونير:1967": "t:المليونير:1950", "t:البوسطجي:1986": "t:البوسطجي:1968", "t:الكاشي ماشي (المضيفات الثلاثة):2018": "t:الكاشي ماشي (المضيفات الثلاثة):2000", "t:المدبح:1978": "t:المدبح:1985", "t:ايام ضايعة:1956": "t:ايام ضايعة:1965", "t:الع\ufffd\ufffdرف:2021": "t:العارف:2021", "t:حظ\ufffd\ufffd تجول:2020": "t:حظر تجول:2020", "t:رأفت الهجان:1988": "s:رافت الهجان - 3 اجزاء", "t:رجل في زمن العولمة:2002": "s:رجل في زمن العولمة - جزان", "t:أيام:2021": "s:ايام ج1–ج2", "t:ريفو ج1–ج2:None": "s:ريڤو ج1–ج2", "t:تامر و شوقية ج1–ج5:None": "s:تامر وشوقية ج1–ج4 + لما تامر ساب شوقية", "s:البرىء": "s:البريء", "s:الف ليلة وليلة - عروس البحور": "s:الف ليلة وليلة: عروس البحور", "s:راجل وست ستات - كل الاجزاء": "s:راجل وست ستات ج1–ج10" , "tt0087800+": "tt1179056", "tt0103639": "tt6139732", "tt0041113": "tt0405676", "tt1263800": "tt0163651", "tt0034465+": "tt0181199", "tt0048960": "tt0327437", "tt0019649": "tt5580536", "tt7584702": "tt10418662", "tt0275491": "tt8206668", "tt1843866": "tt0458339+", "tt0074285": "tt1939659", "tt0082198+": "tt0816462", "tt5078374": "tt27304026", "tt0308379": "tt0382628", "tt0452608+": "tt0072856", "tt0119099+": "tt1564777", "tt0099582+": "tt2039338", "tt1476037": "tt2325002", "tt0038574": "tt1836808", "tt0077651+": "tt1502407", "tt0167190": "tt2274648", "tt0817532": "tt0199626", "tt0089421": "tt0397501", "tt0072271": "tt0099994", "tt0377092+": "tt11762114", "tt0120762+": "tt4566758", "tt0325968": "tt0457433", "tt0069091": "tt0464154", "tt0082933": "tt0368563", "tt0082933+": "tt13125004", "tt0054215+": "tt0155975", "tt0087985+": "tt1234719", "tt0089893": "tt0800175", "tt0955308+": "tt4532826", "tt2582500+": "tt10131024", "tt0108160+": "tt2072233", "tt0076786": "tt1034415", "tt0078767": "tt0384806", "tt0069895": "tt0455407", "tt0061814": "tt3528756", "tt12446086": "tt0120731", "tt0054047+": "tt2404435", "tt0046268": "tt27487473", "tt0004972": "tt4196450", "tt0109587": "tt1700844", "tt0405061+": "tt0406759", "tt0012349+": "tt0219854", "tt0084787+": "tt0905372", "tt0080130": "tt0455857", "tt0451279": "tt7126948", "tt0120616+": "tt32612507", "tt11139354": "tt8579674", "tt0083739": "tt0087803", "t:90 minutes in heaven:2015": "tt4337690", "tt16995656": "s:stranger things season 3", "t:innocent witness:2018": "tt8562562", "tt0110997": "tt21291992", "tt0162650+": "tt0247303", "tt1206326": "tt2395385", "tt1817236": "tt1179069", "tt0110357+": "tt6105098+", "s:marvel studios: legends": "s:marvel studios legends", "s:stranger things season 2": "s:stranger things", "s:stranger things season 3": "s:stranger things", "tt7645122": "tt2395385", "t:غاوي:": "t:غاوي شهرة:", "t:الانسان:": "t:الإنسان واللص:1994", "t:الساكن الجديد:": "t:الساكن الجديد:1977", "t:سهرات بوليسية - الاخوين:": "t:الأخوين:1985", "t:Ya Malek Qalby 2001720p:2001": "t:يا مالك قلبي:2001", "t:غير محدد (devil posfoir):1968": "t:شيطان البوسفور:1968", "tt11506284": "tt0055256"};
const fixKey = (k) => FIXED[k] || k;
const migrate = (d) => {
  d.favorites = (d.favorites || []).map(fixKey); d.watched = (d.watched || []).map(fixKey);
  d.lists = (d.lists || []).map((l) => (l && Array.isArray(l.keys) ? { ...l, keys: l.keys.map(fixKey) } : l));
  d.ratings = Object.fromEntries(Object.entries(d.ratings || {}).map(([k, v]) => [fixKey(k), v]));
  return d;
};
const read = () => migrate({ favorites: [], lists: [], watched: [], ratings: {}, ...JSON.parse(localStorage.getItem(KEY) || "{}") });
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
