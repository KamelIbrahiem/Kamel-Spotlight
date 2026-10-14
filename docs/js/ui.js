import { t } from "./i18n.js";
import { isWatched, myRating } from "./collections.js";
export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
export const $ = (sel, el = document) => el.querySelector(sel);

export function card(m) {
  const img = m.p ? `<img loading="lazy" src="${esc(m.p)}" alt="" onerror="this.remove()">` : "";
  return `<a class="card" href="#/title/${m.id}" data-id="${m.id}">
    <div class="poster"><span class="ph">${esc(m.t)}</span>${img}
      ${m.r ? `<span class="badge">&#9733; ${m.r.toFixed(1)}</span>` : ""}${m.q ? `<span class="q">${esc(m.q)}</span>` : ""}${isWatched(m.id) ? `<span class="seen">&#10003;</span>` : ""}${myRating(m.id) ? `<span class="mine">&#9733;${myRating(m.id)}</span>` : ""}</div>
    <div class="ct">${esc(m.t)}</div><div class="cy">${m.y ?? ""}${m.rd && m.rd !== "N/A" ? ` · <b class="cq">${esc(m.rd)}</b>` : ""}</div><div class="cg">${m.g.slice(0, 2).map(esc).join(" · ")}</div></a>`;
}
export const grid = (list) => `<div class="grid">${list.map(card).join("")}</div>`;
export const row = (title, list, link = "") =>
  `<section class="sec"><h2>${esc(title)}${link ? ` <a href="${link}">&#8250;</a>` : ""}</h2><div class="hrow">${list.map(card).join("")}</div></section>`;
export const chips = (arr, kind) => arr.map((g) => `<a class="chip" href="#/${kind}/${encodeURIComponent(g)}">${esc(g)}</a>`).join("");
export const bars = (pairs) => {
  const max = Math.max(...pairs.map((p) => p[1]), 1);
  return `<div class="bars">${pairs.map(([k, v]) => `<div class="bar"><span>${esc(k)}</span><i style="width:${(v / max) * 100}%"></i><b>${v}</b></div>`).join("")}</div>`;
};
