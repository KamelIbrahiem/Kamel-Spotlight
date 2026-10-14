"""Collections builder: franchise groupings + monthly themes -> collections.json.
Rules live in data/collections-config.json (edit that file, not this code)."""
import json, re
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "data" / "collections-config.json"
MOVIE_TYPES = {"movie", "arabic-movie"}


def _rx(p):
    return re.compile(p, re.I) if p else None


def _key(s):
    s = s.lower().replace("&", "and").replace("ى", "ي").replace("ة", "ه")
    s = re.sub(r"[أإآ]", "ا", s)
    s = re.sub(r"[\u064b-\u065f\u0640]", "", s)
    return re.sub(r"[^\w]+", " ", s).strip()


def _name(s):
    return re.sub(r"\(.*?\)", "", s).lower()


def build(movies, details):
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    franchises = []
    for f in cfg["franchises"]:
        ids = set()
        pool = movies   # every media type: movies, series, plays, programmes (so Arabic author worlds span all of them)
        if f.get("pattern"):
            rx = _rx(f["pattern"])
            ids |= {m["id"] for m in pool if rx.search(m["t"].strip())}
        if f.get("titles"):   # curated list: exact title, optional year
            want = {(_key(t[0]), t[1] if len(t) > 1 else None) for t in f["titles"]}
            ids |= {m["id"] for m in pool if (_key(m["t"]), m["y"]) in want or (_key(m["t"]), None) in want}
        if f.get("text"):     # places / topics: match title, keywords and plot in both languages
            rx, ex = _rx(f["text"]), _rx(f.get("exclude"))
            for m in pool:
                blob = _key(" ".join([m["t"], details[m["id"]].get("kw", ""), details[m["id"]].get("plot", "")]))
                if rx.search(blob) and not (ex and ex.search(blob)): ids.add(m["id"])
        if f.get("title_text"):   # title (+ media subtype) only, both languages
            rx = _rx(f["title_text"])
            ids |= {m["id"] for m in pool if rx.search(_key(m["t"] + " " + details[m["id"]].get("subtype", "")))}
        if f.get("flag"):     # build-time flags derived from the sheet's tags: anime | cartoon | german | 3d
            ids |= {m["id"] for m in pool if f["flag"] in m.get("fl", [])}
        if f.get("writers"):
            ws = [_key(w) for w in f["writers"]]
            ids |= {m["id"] for m in pool if any(w in _key(_name(x)) for x in m["w"] for w in ws)}
        if f.get("actors"):
            ns = [_key(a) for a in f["actors"]]
            ids |= {m["id"] for m in pool if any(n in _key(x) for x in m["a"] for n in ns)}
        if f.get("directors"):
            ds = {d.lower() for d in f["directors"]}
            ids |= {m["id"] for m in pool if any(d.lower() in ds for d in m["d"])}
        if len(ids) >= 2:
            ids = sorted(ids, key=lambda i: (movies[i]["y"] or 9999, movies[i]["t"]))
            franchises.append({"n": f["name"], "ar": f.get("ar", ""), "k": f.get("kind", "saga"), "ids": ids})
    franchises.sort(key=lambda f: (["place", "saga", "author", "director", "actor", "topic"].index(f["k"]), -len(f["ids"])))

    months = {}
    for key, th in cfg["months"].items():
        if not th:
            continue
        genres, gall, kw, aw = set(th.get("genres", [])), set(th.get("genres_all", [])), _rx(th.get("keywords")), _rx(th.get("awards"))
        hits = []
        for m in movies:
            if m["c"] not in MOVIE_TYPES or (m["v"] or 0) < th.get("min_votes", 0) or (m["r"] or 0) < th.get("min_rating", 0):
                continue
            d = details[m["id"]]
            ok = True
            if genres: ok = bool(genres & set(m["g"]))
            if ok and gall: ok = gall <= set(m["g"])
            if ok and kw: ok = bool(kw.search(d.get("kw", "") + " " + m["t"]))
            if ok and aw: ok = bool(aw.search(d.get("aw", "")))
            if ok and not (genres or gall or kw or aw): ok = False
            if ok: hits.append(m)
        hits.sort(key=lambda m: -((m["r"] or 0) * min(m["v"] or 0, 500000) ** 0.25))
        ids = [m["id"] for m in hits[:60]]
        pins = [m["id"] for m in movies if m["t"] in th.get("pin", [])]
        ids = pins + [i for i in ids if i not in pins]
        months[key] = {"n": th["name"], "ar": th["ar"], "b": th["blurb"], "bar": th["blurb_ar"], "ids": ids}
    return {"franchises": franchises, "months": months}
