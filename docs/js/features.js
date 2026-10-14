// Extra views: mood picker, poster wall, TV mode, shared lists, watched, similar titles, fun stats.
import { store, loadStats, loadCollections } from "./data.js";
import { filterAndSort } from "./search.js";
import { t, getLang } from "./i18n.js";
import { watched, isWatched, backend, idsFromKeys, myRating, rated } from "./collections.js";
import { card, grid, row, esc } from "./ui.js";

const ar = () => getLang() === "ar";
const byId = (ids) => ids.map((i) => store.movies[i]).filter(Boolean);
const score = (m) => (m.r || 0) * Math.log10((m.v || 0) + 10);
const hrs = (mins) => Math.round(mins / 60).toLocaleString();

function shuffle(list, seed) {            // seeded, so "Shuffle" gives a new order and a shared URL gives the same one
  let s = Math.floor(+seed * 1e9) || 1;
  const rnd = () => ((s = (s * 1664525 + 1013904223) % 4294967296) / 4294967296);
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

/* ---------- similar titles (scored, not just "same genre") ---------- */
export function similar(m, n = 12) {
  const G = new Set(m.g), A = new Set(m.a), D = new Set(m.d), isSeries = m.c.includes("series");
  const out = [];
  for (const x of store.movies) {
    if (x.id === m.id || x.c.includes("series") !== isSeries) continue;
    const g = x.g.filter((v) => G.has(v)).length;
    if (!g) continue;
    const s = g * 2 + x.d.filter((v) => D.has(v)).length * 4 + x.a.filter((v) => A.has(v)).length * 1.5
      + (x.y && m.y && Math.abs(x.y - m.y) < 10 ? 0.5 : 0) + (x.r || 0) / 10;
    out.push([s, x]);
  }
  return out.sort((a, b) => b[0] - a[0]).slice(0, n).map((p) => p[1]);
}

/* ---------- personal rating widget (10 stars, saved on this device) ---------- */
export function ratingWidget(id) {
  const cur = myRating(id);
  return `<div class="myrate" aria-label="${t("myRating")}"><small>${t("myRating")}</small>${Array.from({ length: 10 }, (_, i) =>
    `<button class="star ${i < cur ? "on" : ""}" data-rate="${id}:${i + 1}" aria-label="${i + 1}">&#9733;</button>`).join("")}${cur ? ` <b>${cur}/10</b>` : ""}</div>`;
}

/* ---------- mood picker ---------- */
const has = (m, ...g) => g.some((x) => m.g.includes(x));
const MOODS = [
  ["romantic", "💕", "Romantic", "رومانسي", (m) => has(m, "Romance")],
  ["action", "💥", "Action", "أكشن", (m) => has(m, "Action", "Adventure")],
  ["laugh", "😂", "Laugh", "ضحك", (m) => has(m, "Comedy")],
  ["cry", "😢", "Emotional", "مؤثر", (m) => has(m, "Drama") && !has(m, "Comedy") && (m.r || 0) >= 7.3],
  ["thrill", "🔍", "Thrilling", "تشويق", (m) => has(m, "Thriller", "Mystery", "Crime")],
  ["scared", "😱", "Scary", "رعب", (m) => has(m, "Horror")],
  ["mind", "🧠", "Mind-bending", "يلخبط العقل", (m) => has(m, "Sci-Fi", "Mystery") && (m.r || 0) >= 7],
  ["family", "👨‍👩‍👧", "Family night", "سهرة عائلية", (m) => has(m, "Family", "Animation")],
  ["epic", "⚔️", "Epic", "ملحمي", (m) => has(m, "War", "History", "Biography") && (m.r || 0) >= 7.2],
  ["feelgood", "☀️", "Feel-good", "يفرفش", (m) => has(m, "Musical", "Music") || (has(m, "Comedy") && has(m, "Romance"))],
  ["classic", "🎞️", "Classics", "كلاسيكيات", (m) => m.y && m.y < 1980 && (m.r || 0) >= 7.5],
];
export function mood(key, p) {
  const chipsHtml = MOODS.map(([k, e, en, a]) => `<a class="chip ${k === key ? "on" : ""}" href="#/mood/${k}">${e} ${ar() ? a : en}</a>`).join("");
  const M = MOODS.find((x) => x[0] === key);
  let body = `<p class="count">${t("moodAsk")}</p>`;
  if (M) {
    const showSeen = p.get("seen") === "1";
    const pool = store.movies.filter((m) => !m.c.includes("series") && m.c !== "play" && m.c !== "program" && M[4](m) && (m.v || 0) > 1000 && (showSeen || !isWatched(m.id)))
      .sort((a, b) => score(b) - score(a)).slice(0, 120);
    const pick = shuffle(pool, p.get("r") || Math.random()).slice(0, 18);
    body = `<p class="count">${pool.length} ${t("results")} · <a class="chip" href="#/mood/${key}?r=${Math.random()}${showSeen ? "&seen=1" : ""}">&#8635; ${t("shuffle")}</a>
      <a class="chip ${showSeen ? "on" : ""}" href="#/mood/${key}${showSeen ? "" : "?seen=1"}">${t("includeWatched")}</a></p>${pick.length ? grid(pick) : `<p class="empty">${t("none")}</p>`}`;
  }
  return `<h1 class="pt">${t("mood")}</h1><div class="chips">${chipsHtml}</div>${body}`;
}

/* ---------- poster wall ---------- */
const WALL_TYPES = { all: null, movies: ["movie", "arabic-movie"], series: ["series", "arabic-series"], arabic: ["arabic-movie", "arabic-series", "play", "program"] };
export function wall(p) {
  const type = WALL_TYPES[p.get("type")] ? p.get("type") : "all", genre = p.get("genre") || "", page = +p.get("page") || 1, seed = p.get("r") || "0.5";
  const list = shuffle(filterAndSort(store.movies, { type: WALL_TYPES[type], genre }).filter((m) => m.p), seed);
  const shown = list.slice(0, page * 400);
  const genres = [...new Set(store.movies.flatMap((m) => m.g))].sort();
  const sel = (name, label, opts, cur) => `<select data-p="${name}"><option value="">${label}</option>${opts.map(([v, l]) => `<option value="${esc(v)}" ${v === cur ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
  return `<h1 class="pt">${t("wall")}</h1><div class="filters">${sel("type", t("all"), [["movies", t("movies")], ["series", t("series")], ["arabic", t("arabic")]], p.get("type") || "")}
    ${sel("genre", t("genre"), genres.map((g) => [g, g]), genre)}<a class="reset" href="#/wall?r=${Math.random()}">&#8635; ${t("shuffle")}</a></div>
    <div class="wall">${shown.map((m) => `<a href="#/title/${m.id}" title="${esc(m.t)} ${m.y ?? ""}"><img loading="lazy" src="${esc(m.p)}" alt="${esc(m.t)}" onerror="this.parentNode.remove()"></a>`).join("")}</div>
    ${shown.length < list.length ? `<button class="btn more" data-more="${page + 1}">${t("loadMore")}</button>` : ""}`;
}

/* ---------- TV mode: big UI, arrow keys + Enter (works with a remote or keyboard) ---------- */
export async function tv() {
  const C = await loadCollections().catch(() => null), mk = String(new Date().getMonth() + 1);
  const rowsDef = [];
  const month = C?.months[mk]; if (month) rowsDef.push([`${t("thisMonth")}: ${ar() && month.ar ? month.ar : month.n}`, byId(month.ids).slice(0, 24)]);
  const good = store.movies.filter((m) => (m.v || 0) > 2000);
  rowsDef.push([t("topRated"), good.slice().sort((a, b) => score(b) - score(a)).slice(0, 30)]);
  rowsDef.push([t("recent"), store.movies.slice(-30).reverse()]);
  rowsDef.push([t("randomArabic"), shuffle(store.movies.filter((m) => m.c.startsWith("arabic") && m.p), Math.random()).slice(0, 30)]);
  const un = good.filter((m) => !isWatched(m.id) && !m.c.includes("series")).sort((a, b) => score(b) - score(a)).slice(0, 30);
  rowsDef.push([t("unwatched"), un]);
  const gen = {}; for (const m of store.movies) for (const g of m.g) gen[g] = (gen[g] || 0) + 1;
  for (const [g] of Object.entries(gen).sort((a, b) => b[1] - a[1]).slice(0, 4)) rowsDef.push([g, shuffle(good.filter((m) => m.g.includes(g)), Math.random()).slice(0, 30)]);
  const tc = (m) => `<a class="tvc" href="#/title/${m.id}" data-tt="${esc(m.t)}" data-ty="${m.y ?? ""}" data-tg="${esc(m.g.slice(0, 3).join(" · "))}" data-tr="${m.r || ""}">
    ${m.p ? `<img loading="lazy" src="${esc(m.p)}" alt="" onerror="this.remove()">` : ""}<span>${esc(m.t)}</span></a>`;
  return `<div class="tv"><a class="tvexit" href="#/">&#10005; ${t("exitTv")}</a><div id="tvinfo" class="tvinfo"><h1></h1><p></p><small>${t("tvHelp")}</small></div>
    ${rowsDef.filter((r) => r[1].length).map(([h, l]) => `<section class="tvrow"><h2>${esc(h)}</h2><div class="tvscroll">${l.map(tc).join("")}</div></section>`).join("")}</div>`;
}
let tvBound = false;
export function tvInit() {
  const focusFirst = () => document.querySelector(".tvc")?.focus();
  if (tvBound) return focusFirst();
  tvBound = true;
  document.addEventListener("focusin", (e) => {
    const c = e.target.closest?.(".tvc"); if (!c) return;
    const i = document.getElementById("tvinfo"); if (!i) return;
    i.querySelector("h1").textContent = `${c.dataset.tt} ${c.dataset.ty}`;
    i.querySelector("p").textContent = `${c.dataset.tg}${c.dataset.tr ? " · \u2605 " + (+c.dataset.tr).toFixed(1) : ""}`;
    c.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });
  });
  document.addEventListener("keydown", (e) => {
    if (!document.body.classList.contains("tvmode")) return;
    if (e.key === "Escape" || e.key === "Backspace") { e.preventDefault(); location.hash = "#/"; return; }
    const dir = { ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [-1, 0], ArrowDown: [1, 0] }[e.key]; if (!dir) return;
    e.preventDefault();
    const rows = [...document.querySelectorAll(".tvscroll")].map((r) => [...r.querySelectorAll(".tvc")]);
    const cur = document.activeElement; let ri = rows.findIndex((r) => r.includes(cur));
    if (ri < 0) { rows[0]?.[0]?.focus(); return; }
    let ci = rows[ri].indexOf(cur);
    if (dir[0]) { ri = Math.max(0, Math.min(rows.length - 1, ri + dir[0])); ci = Math.min(ci, rows[ri].length - 1); }
    else ci = Math.max(0, Math.min(rows[ri].length - 1, ci + dir[1] * (document.dir === "rtl" ? -1 : 1)));
    rows[ri][ci].focus();
  });
  focusFirst();
}

/* ---------- watched, shared lists, hub ---------- */
export function watchedView() {
  const l = byId(watched()), mins = l.reduce((s, m) => s + (m.rt || 0), 0);
  const mine = rated(), avg = mine.length ? (mine.reduce((s, p) => s + p[1], 0) / mine.length).toFixed(1) : "";
  return `<h1 class="pt">${t("watched")}</h1><p class="count">${l.length} ${t("titles")}${mins ? ` · ${hrs(mins)} ${t("hours")}` : ""}${avg ? ` · ${t("avgMine")} ${avg}/10` : ""}</p>
    ${l.length ? grid(l) : `<p class="empty">${t("noWatched")}</p>`}`;
}
export function shared(p) {
  const keys = (p.get("k") || "").split("~~").filter(Boolean), ids = idsFromKeys(keys), name = p.get("n") || t("lists");
  return `<h1 class="pt">${esc(name)}</h1><p class="count">${t("sharedBy")} · ${ids.length} ${t("titles")}${ids.length < keys.length ? ` (${keys.length - ids.length} ${t("notInLibrary")})` : ""}
    <button class="chip" data-saveshared="${esc(name)}" data-keys="${esc(keys.join("~~"))}">+ ${t("saveList")}</button></p>${ids.length ? grid(byId(ids)) : `<p class="empty">${t("none")}</p>`}`;
}
export function shareLink(list) {
  const keys = list.keys || [];
  return `${location.origin}${location.pathname}#/shared?n=${encodeURIComponent(list.name)}&k=${encodeURIComponent(keys.join("~~"))}`;
}
export function hub() {
  const tile = (h, e, l, d) => `<a class="hubtile" href="${h}"><span>${e}</span><b>${l}</b><small>${d}</small></a>`;
  return `<div class="hub">${tile("#/mood", "🎭", t("mood"), t("moodDesc"))}${tile("#/wall", "🖼️", t("wall"), t("wallDesc"))}
    ${tile("#/tv", "📺", t("tvMode"), t("tvDesc"))}${tile("#/watched", "✅", t("watched"), t("watchedDesc"))}${tile("#/stats", "📊", t("stats"), t("statsDesc"))}</div>`;
}

/* ---------- fun stats ---------- */
export async function funStats() {
  const s = await loadStats();
  const films = store.movies.filter((m) => !m.c.includes("series") && m.rt);
  const total = films.reduce((a, m) => a + m.rt, 0);
  const dated = store.movies.filter((m) => m.y && m.y > 1880);
  const oldest = dated.reduce((a, m) => (m.y < a.y ? m : a), dated[0]), newest = dated.reduce((a, m) => (m.y > a.y ? m : a), dated[0]);
  const longest = films.reduce((a, m) => (m.rt > a.rt ? m : a), films[0]);
  const rs = store.movies.filter((m) => m.r), avg = rs.reduce((a, m) => a + m.r, 0) / (rs.length || 1);
  const seen = byId(watched()), seenMin = seen.reduce((a, m) => a + (m.rt || 0), 0);
  const k = (v, l, link) => `<${link ? `a href="${link}"` : "div"} class="fun"><b>${v}</b><small>${l}</small></${link ? "a" : "div"}>`;
  const [actor, n] = s.top_actors[0] || ["", 0];
  const lk = (m) => `${esc(m.t)} (${m.y})`;
  return `<div class="funs">${k(hrs(total), `${t("hoursOfFilms")} (${Math.round(total / 60 / 24)} ${t("days")})`)}
    ${actor ? k(esc(actor), `${t("topActor")} · ${n} ${t("titles")}`, `#/p/${encodeURIComponent(actor)}`) : ""}
    ${k(lk(oldest), t("oldest"), `#/title/${oldest.id}`)}${k(lk(newest), t("newest"), `#/title/${newest.id}`)}
    ${k(`${lk(longest)} · ${longest.rt} ${t("min")}`, t("longest"), `#/title/${longest.id}`)}${k(avg.toFixed(2), t("avgRating"))}
    ${seen.length ? k(`${seen.length} · ${hrs(seenMin)} ${t("hours")}`, t("youWatched"), "#/watched") : ""}</div>`;
}
