import { CONFIG } from "./config.js";
import { t, setLang, getLang } from "./i18n.js";
import { loadCore } from "./data.js";
import { suggest } from "./search.js";
import * as V from "./views.js";
import * as X from "./features.js";
import { toggleFav, toggleWatched, setRating, myRating, backend, owner, setOwner } from "./collections.js";
import { esc, $ } from "./ui.js";

const view = $("#view"), qInput = $("#q"), sug = $("#suggest");
const NAV = [["", "home"], ["movies", "movies"], ["series", "series"], ["arabic", "arabic"], ["cartoons", "cartoons"], ["anime", "anime"], ["logy", "logy"], ["collections", "collections"], ["discover", "discover"], ["favorites", "favorites"], ["lists", "lists"], ["stats", "stats"], ["health", "health"]];

function chrome() {
  document.title = CONFIG.siteName;
  $("#brandName").textContent = CONFIG.siteName.toUpperCase();
  $("#brandTag").textContent = CONFIG.tagline;
  $("#foot").innerHTML = `${esc(t("poweredBy"))} <b>${esc(CONFIG.credit)}</b><br><small class="tmdb">Cast data courtesy of TMDB. This product uses the TMDB API but is not endorsed or certified by TMDB.</small><br><small class="tmdb">Film quotes: English Wikiquote (CC BY-SA 4.0) and the cited Arabic press sources, each linked on its title page.</small>`;
  qInput.placeholder = t("search");
 
  $("#langBtn").textContent = getLang() === "ar" ? "EN" : "AR";
  const cur = location.hash.replace(/^#\/?/, "").split(/[/?]/)[0];
  $("#nav").innerHTML = NAV.map(([h, k]) => `<a href="#/${h}" class="${cur === h ? "on" : ""}">${t(k)}</a>`).join("");
}

async function route() {
  chrome();
  document.body.classList.toggle("tvmode", location.hash.startsWith("#/tv"));
  const [path, qs = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const p = new URLSearchParams(qs), seg = path.split("/").map(decodeURIComponent);
  view.innerHTML = `<p class="empty">${t("loading")}</p>`;
  try {
    if (!seg[0]) view.innerHTML = V.home() + await V.monthRow().catch(() => "");
    else if (["movies", "series", "arabic", "plays", "programs", "cartoons", "anime", "logy", "all"].includes(seg[0])) view.innerHTML = V.library(seg[0], p);
    else if (seg[0] === "german") { location.replace("#/logy?sub=de"); return; }
    else if (seg[0] === "title") view.innerHTML = await V.title(+seg[1]);
    else if (seg[0] === "p") view.innerHTML = await V.person(seg[1]);
    else if (seg[0] === "c") view.innerHTML = V.company(seg[1]);
    else if (seg[0] === "g") { location.replace(`#/all?genre=${encodeURIComponent(seg[1])}`); return; }
    else if (seg[0] === "collections") view.innerHTML = await V.collectionsView(seg[1], seg[2]);
    else if (seg[0] === "mood") view.innerHTML = X.mood(seg[1], p);
    else if (seg[0] === "wall") view.innerHTML = X.wall(p);
    else if (seg[0] === "tv") { view.innerHTML = await X.tv(); X.tvInit(); }
    else if (seg[0] === "watched") view.innerHTML = X.watchedView();
    else if (seg[0] === "shared") view.innerHTML = X.shared(p);
    else if (seg[0] === "discover") view.innerHTML = V.discover(seg[1]);
    else if (seg[0] === "favorites") view.innerHTML = V.favoritesView();
    else if (seg[0] === "lists") view.innerHTML = V.listsView(seg[1]);
    else if (seg[0] === "stats") view.innerHTML = await V.stats();
    else if (seg[0] === "health") view.innerHTML = await V.health();
    else view.innerHTML = V.home();
  } catch (e) { console.error(e); view.innerHTML = `<p class="empty">${t("error")}</p>`; }
  if (seg[0] !== "movies" && seg[0] !== "tv") window.scrollTo(0, 0);
}

// filters + load more write into the URL; the router re-renders
view.addEventListener("change", (e) => {
  const el = e.target.closest("select[data-p]"); if (!el) return;
  const [path, qs = ""] = location.hash.slice(2).split("?"), p = new URLSearchParams(qs);
  el.value ? p.set(el.dataset.p, el.value) : p.delete(el.dataset.p); p.delete("page");
  location.hash = `#/${path}?${p}`;
});
view.addEventListener("click", (e) => {
  const b = e.target.closest("[data-more]"); if (!b) return;
  const [path, qs = ""] = location.hash.slice(2).split("?"), p = new URLSearchParams(qs);
  p.set("page", b.dataset.more); history.replaceState(null, "", `#/${path}?${p}`);
  const y = scrollY; route().then(() => scrollTo(0, y));
});

// favorites, lists
view.addEventListener("click", (e) => {
  const f = e.target.closest("[data-fav]"), a = e.target.closest("[data-addlist]"), d = e.target.closest("[data-dellist]");
  if (f) { toggleFav(+f.dataset.fav); route(); }
  const w = e.target.closest("[data-watch]"); if (w) { toggleWatched(+w.dataset.watch); route(); }
  const r = e.target.closest("[data-rate]"); if (r) { const [id, n] = r.dataset.rate.split(":").map(Number); setRating(id, myRating(id) === n ? 0 : n); route(); }
  const sh = e.target.closest("[data-share]"); if (sh) { const l = backend.all().find((x) => x.id === sh.dataset.share); if (l) { const u = X.shareLink(l); (navigator.clipboard?.writeText(u) || Promise.reject()).then(() => alert(t("linkCopied")), () => prompt(t("share"), u)); } }
  const sv = e.target.closest("[data-saveshared]"); if (sv) { if (!owner()) setOwner(prompt(getLang() === "ar" ? "اسمك؟" : "Your name?") || ""); backend.create(sv.dataset.saveshared, sv.dataset.keys.split("~~").filter(Boolean)); location.hash = "#/lists"; }
  if (d && confirm(t("delete") + "?")) { backend.remove(d.dataset.dellist); location.hash = "#/lists"; }
  if (a) openPicker(+a.dataset.addlist);
});
view.addEventListener("submit", (e) => {
  if (e.target.id !== "newList") return; e.preventDefault();
  if (!owner()) setOwner(prompt(getLang() === "ar" ? "اسمك؟" : "Your name?") || "");
  backend.create(new FormData(e.target).get("n")); route();
});
function openPicker(movieId) {
  const m = $("#modal"), lists = backend.all();
  m.hidden = false;
  m.innerHTML = `<div class="sheet"><h3>${t("pickList")}</h3>${lists.map((l) => `<label class="pl"><input type="checkbox" data-l="${l.id}" ${l.ids.includes(movieId) ? "checked" : ""}> ${esc(l.name)}</label>`).join("") || `<p class="empty">${t("noLists")}</p>`}
    <a class="btn ghost" href="#/lists">${t("lists")}</a> <button class="btn" data-close>${t("close")}</button></div>`;
  m.onclick = (ev) => { const c = ev.target.closest("input[data-l]"); if (c) backend.toggle(c.dataset.l, movieId); if (ev.target === m || ev.target.closest("[data-close],a")) m.hidden = true; };
}

// search box: suggestions while typing, Enter opens full results
qInput.addEventListener("input", () => {
  const { people, titles } = suggest(qInput.value);
  if (!people.length && !titles.length) { sug.hidden = true; return; }
  sug.innerHTML = people.map((x) => `<a href="#/p/${encodeURIComponent(x.name)}">&#128100; ${esc(x.name)} <small>${x.n}</small></a>`).join("") +
    titles.map((m) => `<a href="#/title/${m.id}">${esc(m.t)} <small>${m.y ?? ""}</small></a>`).join("");
  sug.hidden = false;
});
sug.addEventListener("click", () => { sug.hidden = true; qInput.value = ""; });
$("#searchForm").addEventListener("submit", (e) => { e.preventDefault(); sug.hidden = true; location.hash = `#/movies?q=${encodeURIComponent(qInput.value)}`; qInput.blur(); });
$("#themeBtn").addEventListener("click", () => { const n = document.documentElement.dataset.theme === "dark" ? "light" : "dark"; document.documentElement.dataset.theme = n; localStorage.setItem("ks-theme", n); });
$("#langBtn").addEventListener("click", () => { setLang(getLang() === "ar" ? "en" : "ar"); route(); });
window.addEventListener("hashchange", route);

loadCore().then(route).catch(() => { view.innerHTML = `<p class="empty">${t("error")}</p>`; });
