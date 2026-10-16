// Service worker: app shell cached for offline start + fast loads; data is network-first so syncs show up.
const V = "ks-v158", SHELL = ["./", "index.html", "css/style.css", "js/app.js", "js/config.js", "js/i18n.js", "js/data.js", "js/search.js", "js/views.js", "js/ui.js", "js/collections.js", "js/features.js", "img/logo.svg", "manifest.webmanifest"];
self.addEventListener("install", (e) => { e.waitUntil(caches.open(V).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((k) => Promise.all(k.filter((x) => x !== V).map((x) => caches.delete(x)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;       // posters etc. load normally
  const network = u.pathname.includes("/data/");
  e.respondWith(network
    ? fetch(e.request).then((r) => { const c = r.clone(); caches.open(V).then((x) => x.put(e.request, c)); return r; }).catch(() => caches.match(e.request))
    : fetch(e.request).then((r) => { const c = r.clone(); caches.open(V).then((x) => x.put(e.request, c)); return r; }).catch(() => caches.match(e.request)));
});
