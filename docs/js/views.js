import { store, loadStats, loadHealth, loadDetails, loadCollections } from "./data.js";
import { search, filterAndSort } from "./search.js";
import { CONFIG } from "./config.js";
import { t, getLang } from "./i18n.js";
import { favorites, isFav, backend } from "./collections.js";
import { card, grid, row, chips, bars, esc } from "./ui.js";
import { similar, ratingWidget, funStats, hub } from "./features.js";
import { isWatched, backend as _b } from "./collections.js";

const TYPES = { all: null, movies: ["movie", "arabic-movie"], series: ["series", "arabic-series"], arabic: ["arabic-movie", "arabic-series", "play", "program"], plays: ["play"], programs: ["program"] };
const top = (list, n = 20) => list.filter((m) => m.v > 2000).sort((a, b) => b.r - a.r).slice(0, n);
const pick = (list) => list[Math.floor(Math.random() * list.length)];

export function home() {
  const all = store.movies;
  const gen = {};
  for (const m of all) for (const g of m.g) gen[g] = (gen[g] || 0) + 1;
  const genres = Object.entries(gen).sort((a, b) => b[1] - a[1]).slice(0, 14);
  const tonight = pick(top(all, 300));
  return `<section class="hero"><div><small>${t("pickTitle")}</small><h1>${esc(tonight.t)} <em>${tonight.y ?? ""}</em></h1>
      <p>${tonight.g.map(esc).join(" · ")}${tonight.r ? ` · &#9733; ${tonight.r.toFixed(1)}` : ""}</p>
      <a class="btn" href="#/title/${tonight.id}">&#9654; ${t("details")}</a> <a class="btn ghost" href="#/discover">${t("discover")}</a></div>
      ${tonight.p ? `<img src="${esc(tonight.p)}" alt="" onerror="this.remove()">` : ""}</section>
    ${row(t("topRated"), top(all), "#/movies?sort=rated")}
    ${row(t("recent"), all.slice(-20).reverse(), "#/movies")}
    <section class="sec"><h2>${t("genres")}</h2><div class="chips">${genres.map(([g, n]) => `<a class="chip" href="#/movies?genre=${encodeURIComponent(g)}">${esc(g)} <small>${n}</small></a>`).join("")}</div></section>`;
}

// Library: search + filters, URL-driven so links are shareable.
export function library(kind, params) {
  const f = { type: TYPES[kind], country: params.get("country") || "", ramadan: params.get("ramadan") || "", rated: params.get("rated") || "", genre: params.get("genre") || "", quality: params.get("quality") || "",
    era: +params.get("era") || 0, minRating: +params.get("min") || 0, sort: params.get("sort") || "", watch: params.get("watch") || "" };
  const q = params.get("q") || "";
  const filtered = !!(q || f.genre || f.quality || f.era || f.minRating || f.country || f.rated || f.ramadan || f.watch);
  if (!f.sort && filtered && !q) f.sort = "rated";   // plain list keeps sheet order; any filter defaults to Highest rated
  const base = q ? search(q) : store.movies;
  const list = filterAndSort(base, f);
  const genres = [...new Set(store.movies.flatMap((m) => m.g))].sort();
  const quals = ["2160p", "1080p", "720p", "3D"];
  const eras = [2020, 2010, 2000, 1990, 1980, 1970, 1960, 1950, 1940];
  const sel = (name, label, opts, cur) => `<select data-p="${name}"><option value="">${label}</option>${opts.map(([v, l]) => `<option value="${esc(v)}" ${String(v) === String(cur) ? "selected" : ""}>${esc(l)}</option>`).join("")}</select>`;
  const page = +params.get("page") || 1;
  const shown = list.slice(0, page * CONFIG.pageSize);
  return `<div class="filters" data-kind="${kind}">
    ${sel("genre", t("genre"), genres.map((g) => [g, g]), f.genre)}
    ${sel("quality", t("quality"), quals.map((x) => [x, x]), f.quality)}
    ${sel("era", t("era"), eras.map((e) => [e, e + "s"]), f.era || "")}
    ${sel("min", t("minRating"), [9, 8, 7, 6, 5].map((x) => [x, x + "+"]), f.minRating || "")}
    ${sel("watch", t("watchState"), [["seen", t("watched")], ["unseen", t("unwatched")]], f.watch)}
    ${sel("sort", t("sort"), [["rated", t("sortRated")], ["votes", t("sortVotes")], ["new", t("sortNew")], ["old", t("sortOld")], ["az", t("sortAZ")]], f.sort)}
    <a class="reset" href="#/${kind}${q ? "?q=" + encodeURIComponent(q) : ""}">${t("reset")}</a></div>
    ${["country", "rated", "ramadan"].filter((k) => f[k]).map((k) => `<span class="chip on">${esc(f[k])}</span>`).join(" ")}
    <p class="count">${q ? `&ldquo;${esc(q)}&rdquo; · ` : ""}${list.length.toLocaleString()} ${t("results")}</p>
    ${list.length ? grid(shown) : `<p class="empty">${t("none")}</p>`}
    ${shown.length < list.length ? `<button class="btn more" data-more="${page + 1}">${t("loadMore")}</button>` : ""}`;
}

export function person(name) {
  const l = store.movies.filter((m) => m.a.includes(name) || m.d.includes(name) || m.w.includes(name)).sort((a, b) => (b.y || 0) - (a.y || 0));
  return `<h1 class="pt">${esc(name)}</h1><p class="count">${l.length} ${t("titles")}</p>${grid(l)}`;
}

export async function title(id) {
  const m = store.movies[id]; if (!m) return `<p class="empty">${t("none")}</p>`;
  const d = await loadDetails(id);
  const sim = similar(m);
  const C = await loadCollections().catch(() => null);
  const parts = (C?.franchises || []).map((f, i) => [f, i]).filter(([f]) => f.ids.includes(id));
  const yt = `https://www.youtube.com/results?search_query=${encodeURIComponent(`${m.t} ${m.y ?? ""} official trailer`)}`;
  const link = (label, qs) => `<a class="chip" href="#/all?${qs}">${esc(label)}</a>`;
  const kws = (d.kw || "").split(",").map((x) => x.trim()).filter(Boolean);
  const info = [
    [t("release"), esc(d.rel)], [t("runtime"), m.rt ? `${m.rt} ${t("min")}` : ""],
    [t("country"), m.co.map((c) => link(c, "country=" + encodeURIComponent(c))).join("")],
    [t("rated"), d.rated ? link(d.rated, "rated=" + encodeURIComponent(d.rated)) : ""],
    [t("boxOffice"), esc(d.bo)], [t("awards"), esc(d.aw)],
    [t("quality"), m.q ? link(m.q, "quality=" + encodeURIComponent(m.q)) : ""],
    [t("seasons"), Array.isArray(d.seasons) && d.seasons.length ? d.seasons.join(", ") : ""], [t("episodes"), m.ep ? String(m.ep) : ""], [t("ramadan"), m.rm ? link(t("ramadan"), "ramadan=1") : ""], [t("language"), esc(m.lg)], [t("spoken"), esc(d.spoken)], [t("mediaType"), link(m.c.includes("series") ? t("seriesOne") : t("movie"), "")],
    [t("contentType"), esc(m.c)],
    ["IMDb ID", d.imdb ? `<a href="https://www.imdb.com/title/${esc(d.imdb)}/" target="_blank" rel="noopener">${esc(d.imdb)}</a>` : ""],
    ["TMDb ID", d.tmdb ? esc(d.tmdb) : ""], [t("notes"), esc(d.notes)],
  ].filter((r) => r[1]);
  return `<article class="detail"><div class="dhead">${m.p ? `<img class="dposter" src="${esc(m.p)}" alt="" onerror="this.remove()">` : ""}
    <div><h1>${esc(m.t)} <em>${m.y ?? ""}</em></h1>${m.o ? `<p class="orig">${esc(m.o)}</p>` : ""}
    <p class="meta">${m.r ? `<span class="rate">&#9733; ${m.r.toFixed(1)}</span> <small>(${(m.v || 0).toLocaleString()} ${t("imdbVotes")})</small>` : ""} ${m.rt ? ` · ${m.rt} ${t("min")}` : ""}</p>
    <div class="chips">${chips(m.g, "g")}</div>${ratingWidget(id)}${parts.length ? `<div class="chips">${parts.map(([f, i]) => `<a class="chip gold" href="#/collections/f/${i}">&#128218; ${esc(getLang() === "ar" && f.ar ? f.ar : f.n)}</a>`).join("")}</div>` : ""}
    <p><a class="btn" href="${yt}" target="_blank" rel="noopener">&#9654; ${t("trailer")}</a> <button class="btn ghost ${isWatched(id) ? "on" : ""}" data-watch="${id}">${isWatched(id) ? "&#10003; " + t("watchedOne") : "&#9744; " + t("markWatched")}</button> <button class="btn ghost" data-fav="${id}">${isFav(id) ? "&#9829; " + t("faved") : "&#9825; " + t("fav")}</button> <button class="btn ghost" data-addlist="${id}">+ ${t("addToList")}</button></p></div></div>
    ${d.plot ? (getLang() === "ar" && d.plot_ar ? `<h3>${t("plot")}</h3><p class="plot" dir="rtl">${esc(d.plot_ar)}</p><p class="mt-note">${t("machineTr")}</p>` : `<h3>${t("plot")}</h3><p class="plot">${esc(d.plot)}</p>`) : ""}
    <h3>${t("cast")}</h3><div class="chips">${chips(m.a, "p")}</div>
    ${m.d.length ? `<h3>${t("director")}</h3><div class="chips">${chips(m.d, "p")}</div>` : ""}${m.w.length ? `<h3>${t("writer")}</h3><div class="chips">${chips(m.w, "p")}</div>` : ""}
    ${m.pr.length ? `<h3>${t("company")}</h3><div class="chips">${chips(m.pr, "c")}</div>` : ""}
    ${kws.length ? `<h3>${t("keywords")}</h3><div class="chips">${kws.map((k) => `<a class="chip" href="#/all?q=${encodeURIComponent(k)}">${esc(k)}</a>`).join("")}</div>` : ""}
    <h3>${t("tech")}</h3><dl class="info">${info.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>
    ${sim.length ? row(t("similar"), sim) : ""}</article>`;
}

export function discover(kind) {
  const pools = { movie: store.movies.filter((m) => m.c === "movie"), series: store.movies.filter((m) => m.c === "series"),
    arabic: store.movies.filter((m) => m.c.startsWith("arabic")) };
  const k = pools[kind]?.length ? kind : "movie";
  const m = pick(pools[k].filter((x) => (x.v || 0) > 1000).length ? pools[k].filter((x) => (x.v || 0) > 1000) : pools[k]);
  return `${hub()}<section class="disc"><div class="dbtns"><a class="btn ${k === "movie" ? "" : "ghost"}" href="#/discover/movie">${t("randomMovie")}</a>
    <a class="btn ${k === "series" ? "" : "ghost"}" href="#/discover/series">${t("randomSeries")}</a>
    <a class="btn ${k === "arabic" ? "" : "ghost"}" href="#/discover/arabic">${t("randomArabic")}</a></div>
    ${m ? `<div class="pick">${card(m)}<p>${m.g.map(esc).join(" · ")}</p><a class="btn" href="#/discover/${k}?r=${Math.random()}">&#8635; ${t("another")}</a></div>` : `<p class="empty">${t("none")}</p>`}</section>`;
}

export function company(name) {
  const l = store.movies.filter((m) => m.pr.includes(name)).sort((a, b) => (b.y || 0) - (a.y || 0));
  return `<h1 class="pt">${esc(name)}</h1><p class="count">${l.length} ${t("titles")}</p>${grid(l)}`;
}

export async function stats() {
  const s = await loadStats();
  return `<h1 class="pt">${t("stats")}</h1><div class="kpis"><div><b>${s.total.toLocaleString()}</b>${t("total")}</div>
    ${Object.entries(s.by_type).map(([k, v]) => `<div><b>${v.toLocaleString()}</b>${t(k + "-t") === k + "-t" ? esc(k) : t(k + "-t")}</div>`).join("")}</div>
    ${await funStats()}<p class="count">${t("built")}: ${s.built} · ${s.duplicates_removed} ${t("dupes")}</p>
    <h3>${t("topGenres")}</h3>${bars(s.top_genres)}<h3>${t("topActors")}</h3>${bars(s.top_actors)}
    <h3>${t("topDirectors")}</h3>${bars(s.top_directors)}<h3>${t("countries")}</h3>${bars(s.countries)}
    <h3>${t("decades")}</h3>${bars(s.decades)}<h3>${t("ratings")}</h3>${bars(s.ratings.map(([k, v]) => [k + "+", v]))}`;
}

export async function health() {
  const h = await loadHealth(), total = store.movies.length;
  return `<h1 class="pt">${t("health")}</h1><div class="hl">${Object.entries(h).map(([k, ids]) => `<div class="${ids.length ? "warn" : "good"}">
    <span>${t(k)}</span><b>${ids.length ? ids.length : t("ok")}</b>${ids.length ? `<small>${((ids.length / total) * 100).toFixed(1)}%</small>` : ""}
    ${ids.slice(0, 5).map((i) => `<a href="#/title/${i}">${esc(store.movies[i]?.t)}</a>`).join("")}</div>`).join("")}</div>`;
}

export function favoritesView() {
  const l = favorites().map((i) => store.movies[i]).filter(Boolean);
  return `<h1 class="pt">${t("favorites")}</h1>${l.length ? grid(l) : `<p class="empty">${t("noFavs")}</p>`}`;
}

export function listsView(openId) {
  const lists = backend.all();
  const open = lists.find((l) => l.id === openId);
  if (open) return `<p><a href="#/lists">&#8249; ${t("lists")}</a></p><h1 class="pt">${esc(open.name)}</h1><p class="count">${open.owner ? esc(open.owner) + " · " : ""}${open.ids.length} ${t("titles")} <button class="chip" data-share="${open.id}">&#128279; ${t("share")}</button> <button class="chip" data-dellist="${open.id}">${t("delete")}</button></p>${grid(open.ids.map((i) => store.movies[i]).filter(Boolean))}`;
  return `<h1 class="pt">${t("lists")}</h1><form class="newlist" id="newList"><input name="n" placeholder="${t("newList")}" required><button class="btn">${t("create")}</button></form>
    ${lists.length ? `<div class="chips">${lists.map((l) => `<a class="chip" href="#/lists/${l.id}">${esc(l.name)} <small>${l.ids.length}</small></a>`).join("")}</div>` : `<p class="empty">${t("noLists")}</p>`}
    <p class="count">${t("localNote")}</p>`;
}

// Collections: franchises (complete sagas) + monthly themes. Rules live in data/collections-config.json.
const nm = (o) => (getLang() === "ar" && o.ar) ? o.ar : o.n;
const mnames = () => t("monthNames").split(",");
const byIds = (ids) => ids.map((i) => store.movies[i]).filter(Boolean);

export async function collectionsView(kind, key) {
  const C = await loadCollections(), ar = getLang() === "ar";
  if (kind === "f") {
    const f = C.franchises[+key]; if (!f) return `<p class="empty">${t("none")}</p>`;
    return `<section class="sec"><h2>${esc(nm(f))} <small>${f.ids.length} ${t("parts")}</small></h2><p class="muted"><a href="#/collections">&#8249; ${t("collections")}</a></p>${byIds(f.ids).length ? grid(byIds(f.ids)) : `<p class="empty">${t("staleData")}</p>`}</section>`;
  }
  if (kind === "m") {
    const m = C.months[key]; if (!m) return `<p class="empty">${t("none")}</p>`;
    return `<section class="sec"><h2>${esc(nm(m))}</h2><p class="muted">${esc(ar ? m.bar : m.b)} &middot; <a href="#/collections">&#8249; ${t("collections")}</a></p>${grid(byIds(m.ids))}</section>`;
  }
  const cur = String(new Date().getMonth() + 1), names = mnames();
  const chipsM = Object.keys(C.months).map((k) => `<a class="chip ${k === cur ? "on" : ""}" href="#/collections/m/${k}">${names[k - 1]} &middot; ${esc(nm(C.months[k]))}</a>`).join("");
  const cm = C.months[cur];
  const tileOf = (f, i) => `<a class="ftile" href="#/collections/f/${i}"><div class="fstrip">${byIds(f.ids).filter((m) => m.p).slice(0, 3).map((m) => `<img loading="lazy" src="${esc(m.p)}" alt="" onerror="this.remove()">`).join("")}</div><b>${esc(nm(f))}</b><small>${f.ids.length} ${t("parts")}</small></a>`;
  const sect = (kindKey, label) => { const l = C.franchises.map((f, i) => [f, i]).filter(([f]) => f.k === kindKey); return l.length ? `<section class="sec"><h2>${label}</h2><div class="ftiles">${l.map(([f, i]) => tileOf(f, i)).join("")}</div></section>` : ""; };
  return `${cm ? row(`${t("thisMonth")}: ${nm(cm)}`, byIds(cm.ids).slice(0, 20), `#/collections/m/${cur}`) : ""}
    <section class="sec"><h2>${t("months")}</h2><div class="chips">${chipsM}</div></section>
    ${sect("place", t("placeWorlds"))}${sect("saga", t("franchises"))}${sect("author", t("authorWorlds"))}${sect("director", t("directorWorlds"))}${sect("actor", t("starWorlds"))}${sect("topic", t("topicWorlds"))}`;
}
export async function monthRow() {
  const C = await loadCollections(), k = String(new Date().getMonth() + 1), m = C.months[k];
  return m ? row(`${t("thisMonth")}: ${nm(m)}`, byIds(m.ids).slice(0, 20), `#/collections/m/${k}`) : "";
}
