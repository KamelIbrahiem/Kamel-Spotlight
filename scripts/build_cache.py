#!/usr/bin/env python3
"""Cache builder: sheet CSV -> JSON files the website reads.

Usage:  python3 scripts/build_cache.py [path-or-url-to-csv]
Output: docs/data/{movies,details,search-index,genres,people,statistics,health}.json
The site never reads the sheet directly; it only reads these files.
"""
import csv, hashlib, io, json, re, sys, unicodedata, urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_collections

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "data"
DEFAULT_SRC = ROOT / "data" / "sheet.csv"
QUALITY_RANK = {"2160p": 6, "1080p": 5, "720p": 4, "576p": 3, "480p": 2, "360p": 1}
ARABIC_COUNTRIES = {"Egypt", "Saudi Arabia", "Lebanon", "Syria", "Kuwait", "United Arab Emirates",
                    "Jordan", "Morocco", "Tunisia", "Algeria", "Iraq", "Palestine"}
CONTENT_TYPES = ["movie", "series", "arabic-movie", "arabic-series", "play", "program", "other"]

_PA = Path(__file__).resolve().parent.parent / "data" / "plot-ar.json"
PLOT_AR = json.loads(_PA.read_text(encoding="utf-8")) if _PA.exists() else {}   # machine translations, see translate_plots.py

_PC = Path(__file__).resolve().parent.parent / "data" / "cast-tmdb.json"
CAST_TMDB = json.loads(_PC.read_text(encoding="utf-8")) if _PC.exists() else {}   # fuller cast lists, see fetch_cast.py

def clean_title(t):
    """Public titles: drop site tags like ' - IMedia.Movies' and trailing '[2000]' year tags."""
    t = re.sub(r"\s*[-\u2013]\s*\S+\.(movies|com|net|org|tv)\s*$", "", t or "", flags=re.I)
    t = re.sub(r"\s*\[(19|20)\d\d\]\s*$", "", t).strip()
    # Scene-style names (dots + year/resolution/source/group): keep only the title part, never the tags.
    if re.search(r"WEB-?DL|WATCH ?IT|SHAHID|TvRip|BluRay|Torren|(?:19|20)\\d\\d\\d{3,4}p|\b(19|20)\d\d\b.*\b\d{3,4}p\b|\]\[|\.(19|20)\d\d\.", t, re.I):
        t = re.split(r"\s*\[|\s+WEB-?DL|[. ](?:19|20)\d\d(?:\D|$)|[. ]\d{3,4}p\b", t, 1, flags=re.I)[0]
        if t.count(".") >= 1 and " " not in t.strip(): t = t.replace(".", " ")
        t = t.replace(".", " ")
        t = re.sub(r"\s*(?:19|20)\d\d\d{3,4}p.*$|\s*\S*Torren.*$", "", t, flags=re.I).strip(" .-_")
    return t

def load(src):
    if str(src).startswith("http"):
        raw = urllib.request.urlopen(src).read().decode("utf-8-sig")
    else:
        raw = Path(src).read_text(encoding="utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(raw)))
    for r in rows: r["Title"] = clean_title(r.get("Title"))
    return rows

def lst(s):
    return [x.strip() for x in (s or "").split(",") if x.strip()]

def norm(s):
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\u0640\u064b-\u065f]", "", s).replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")

def num(s):
    m = re.search(r"[\d.]+", (s or "").replace(",", ""))
    return float(m.group()) if m else None

def rating(s):
    m = re.match(r"\s*([\d.]+)\s*\(([\d,]+)", s or "")
    return (float(m.group(1)), int(m.group(2).replace(",", ""))) if m else (None, None)

ARAB_COUNTRIES = {"Egypt", "Lebanon", "Syria", "Kuwait", "Saudi Arabia", "Jordan", "Iraq", "Morocco", "Tunisia", "Algeria", "United Arab Emirates",
                  "Palestine", "Sudan", "Libya", "Qatar", "Bahrain", "Oman", "Yemen"}

def content_type(row):
    """Buckets come from Media Type (H) + Source Collection (AM); Arabic detection from title/country is only a fallback."""
    mt = (row.get("Media Type") or "").strip().lower()
    col = (row.get("Source Collection") or "").strip().lower()
    cat = (row.get("Source Category") or "").strip()
    lang = (row.get("Original language") or "").split(",")[0].strip().lower()
    # Arabic = Source Collection says so, or a native Arabic title (languages are listed alphabetically, so they are not a signal).
    # (Country is NOT used: foreign films shot in the UAE list it first and are not Arabic works.)
    arabic = "arabic" in col or (not col and (any("\u0600" <= c <= "\u06ff" for c in row.get("Title", ""))))
    # Guard against a wrong Arabic tag: a Latin-script title whose original language is known, is not Arabic and has no Arab country.
    if arabic and "arabic" in col and lang and lang != "arabic" and "arabic" not in (row.get("Original language") or "").lower() \
            and not re.search("[\u0600-\u06ff]", (row.get("Title") or "") + (row.get("Actors") or "")) \
            and not any(c in ARAB_COUNTRIES for c in lst(row.get("Country"))):
        arabic = False
    if mt in ("play", "program"): return mt
    if not mt: return "other"        # no media type in the sheet: kept visible, unclassified (listed in All only)
    if mt == "series": return "arabic-series" if arabic else "series"
    return "arabic-movie" if arabic else "movie"

def seasons_of(raw):
    """'S02,S93' -> [2]; tokens above S40 are release-group noise, not seasons."""
    out = []
    for t in re.findall(r"S(\d{1,2})", raw or ""):
        if 0 < int(t) <= 40 and int(t) not in out: out.append(int(t))
    return out

def is_ramadan(row):
    return bool((row.get("Ramadan Category") or "").strip() or (row.get("Ramadan Subtype") or "").strip())

def poster(p):
    p = (p or "").strip()
    return p if p.startswith("http") else ""

def main():
    rows = load(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC)
    # Duplicate rule: movies/plays/programmes - same Title+Year keep highest quality.
    # Series: season-level rows are grouped into ONE show by Title (never by Year: series years are parser noise).
    best, dupes, shows = {}, 0, {}
    for i, r in enumerate(rows):
        if not r.get("Title"): continue
        ct = content_type(r)
        if ct.endswith("series") or ct == "series":
            key = (norm(r["Title"]), ct)
            sh = shows.setdefault(key, {"row": r, "i": i, "seasons": set(), "eps": 0, "n": 0, "years": [], "ram": False})
            sh["n"] += 1; sh["seasons"].update(seasons_of(r.get("Seasons")))
            sh["eps"] += int(num(r.get("Episode Count")) or 0); sh["ram"] |= is_ramadan(r)
            if (r.get("Year") or "").isdigit(): sh["years"].append(int(r["Year"]))
            if not poster(sh["row"].get("Poster")) and poster(r.get("Poster")): sh["row"] = r
            continue
        key = (norm(r["Title"]), r.get("Year", ""), ct)
        q = QUALITY_RANK.get((r.get("Quality") or "").strip(), 0)
        if key in best:
            dupes += 1
            if q <= best[key][0]: continue
        best[key] = (q, i, r)
    items = [(q, i, r, None) for q, i, r in best.values()] + \
            [(0, sh["i"], sh["row"], sh) for sh in shows.values()]
    items.sort(key=lambda t: t[1])

    movies, details, search, health = [], {}, [], defaultdict(list)
    seen_keys = set()
    people = {"actors": defaultdict(list), "directors": defaultdict(list)}
    for n, (_, i, r, show) in enumerate(items):
        mid = n
        k = ("s:" + norm(r["Title"])) if show else ((r.get("IMDb ID") or "").strip() or f"t:{norm(r['Title'])}:{r.get('Year', '')}")
        while k in seen_keys: k += "+"
        seen_keys.add(k)
        rt, votes = rating(r.get("IMDb Rating (Votes)"))
        genres, actors, directors = lst(r.get("Genre")), lst(r.get("Actors")), lst(r.get("Director"))
        extra = CAST_TMDB.get(k.rstrip("+"))   # same key as the movie: IMDb ID, t:title:year or s:title
        if extra and len(extra) > len(actors): actors = extra
        year = int(r["Year"]) if (r.get("Year") or "").isdigit() else None
        ct = content_type(r)
        ram = show["ram"] if show else is_ramadan(r)
        seas = sorted(show["seasons"]) if show else seasons_of(r.get("Seasons"))
        tags = {x.strip().lower() for x in (r.get("Source Collection") or "").split(";")}
        fl = [f for f, on in (("anime", "anime" in tags), ("cartoon", bool(tags & {"cartoon", "animation"})), ("german", bool(tags & {"german film", "kino"})),
                               ("3d", (r.get("Quality") or "").strip().lower() == "3d" or bool(tags & {"3d", "3d movies"}))) if on]
        movies.append({"id": mid, "fl": fl, "k": k, "t": r["Title"], "o": r.get("Original Name", ""), "y": year, "c": ct,
                       "g": genres, "a": actors, "d": directors, "r": rt, "v": votes,
                       "q": (r.get("Quality") or "").strip(), "p": poster(r.get("Poster")),
                       "rd": (r.get("Rated") or "").strip(), "w": lst(r.get("Writer / Creator")), "pr": lst(r.get("Production Company")), "rm": 1 if ram else 0, "sn": len(seas), "ep": show["eps"] if show else int(num(r.get("Episode Count")) or 0), "lg": (r.get("Original language") or "").strip(), "rt": num(r.get("Runtime")), "co": lst(r.get("Country")), "n": i})
        plot = (r.get("Plot") or "").strip()
        par = PLOT_AR.get(hashlib.sha1(plot.encode("utf-8")).hexdigest()[:16]) if plot and plot != "N/A" and not re.search("[\u0600-\u06ff]", plot) else None
        if par and not re.search("[\u0600-\u06ff]", par): par = None   # engine echoed English: show the original instead
        details[mid] = {"plot": r.get("Plot", ""), **({"plot_ar": par} if par else {}), "kw": r.get("Keywords", ""), "rd": (r.get("Rated") or "").strip(), "w": lst(r.get("Writer / Creator")),
                        "aw": r.get("Awards", ""), "rated": r.get("Rated", ""), "rel": r.get("Release Date", ""),
                        "bo": (r.get("Box Office") or "").strip(), "imdb": r.get("IMDb ID", ""),
                        
                        "prod": r.get("Production Company", ""), "seasons": seas, "spoken": r.get("Spoken languages", ""), "subtype": r.get("Media Subtype", ""), "tmdb": r.get("TMDb ID", ""), "notes": r.get("Notes", "")}
        search.append(norm(" | ".join([r["Title"], r.get("Original Name", ""), r.get("Actors", ""), r.get("Director", ""),
                                       r.get("Writer / Creator", ""), r.get("Production Company", ""), r.get("Genre", ""), r.get("Keywords", ""),
                                       r.get("IMDb ID", "")])))
        for a in actors: people["actors"][a].append(mid)
        for w in lst(r.get("Writer / Creator")): people.setdefault("writers", defaultdict(list))[w].append(mid)
        for d in directors: people["directors"][d].append(mid)
        for field, ok in [("poster", poster(r.get("Poster"))), ("plot", r.get("Plot")), ("keywords", r.get("Keywords")),
                          ("imdb_id", r.get("IMDb ID")), ("country", r.get("Country")),
                          ("release_date", r.get("Release Date"))]:
            if not ok: health[f"missing_{field}"].append(mid)

    gcount = Counter(g for m in movies for g in m["g"])
    stats = {
        "total": len(movies), "duplicates_removed": dupes, "series_rows_grouped": sum(sh["n"] for sh in shows.values()),
        "by_type": Counter(m["c"] for m in movies),
        "top_genres": gcount.most_common(15),
        "top_actors": sorted(((a, len(v)) for a, v in people["actors"].items()), key=lambda x: -x[1])[:15],
        "top_directors": sorted(((a, len(v)) for a, v in people["directors"].items()), key=lambda x: -x[1])[:15],
        "countries": Counter(c for m in movies for c in m["co"]).most_common(12),
        "decades": sorted(Counter(f"{m['y']//10*10}s" for m in movies if m["y"]).items()),
        "ratings": sorted(Counter(int(m["r"]) for m in movies if m["r"]).items()),
        "qualities": Counter(m["q"] or "?" for m in movies).most_common(8),
        "built": date.today().isoformat(),
    }
    top_people = lambda d: {k: v for k, v in d.items() if len(v) >= 2}
    files = {"movies": movies, "search-index": search,
             "genres": dict(gcount), "people": {k: top_people(v) for k, v in people.items()},
             "statistics": stats, "health": {k: v for k, v in health.items()},
             "collections": build_collections.build(movies, details)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "details").mkdir(exist_ok=True)
    for f in (OUT / "details").glob("*.json"): f.unlink()
    CH = 250  # details are lazy-loaded in chunks of 250 titles: details/<id // 250>.json
    for c in range(0, len(movies), CH):
        chunk = {i: details[i] for i in range(c, min(c + CH, len(movies)))}
        (OUT / "details" / f"{c // CH}.json").write_text(json.dumps(chunk, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    for name, data in files.items():
        (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(name, (OUT / f"{name}.json").stat().st_size // 1024, "KB")
    print("titles", len(movies), "duplicates removed", dupes)

if __name__ == "__main__":
    main()
