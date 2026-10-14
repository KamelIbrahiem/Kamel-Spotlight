"""Fetch top-billed cast from TMDB for foreign movies and series whose cast in the sheet is short (<4 names). Resumable.
Usage:  TMDB_KEY=<v3 api key> python3 scripts/fetch_cast.py [csv]
Matching: by IMDb ID when the row has one (/find). Otherwise TMDB /search by title + year; accepted only when exactly one
result has the same normalised title AND the same year (series: same title, unique); everything else is listed in
data/cast-unmatched.json and left alone. Arabic titles are skipped.
Cache: data/cast-tmdb.json  {key: [name, ...]} (max 12 names, billing order). key = IMDb ID, "t:<title>:<year>" for movies
without an ID, "s:<title>" for series (same keys the site build uses). The key is read from the environment only and never written."""
import csv, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cast-tmdb.json"
UNMATCHED = ROOT / "data" / "cast-unmatched.json"
KEY = os.environ.get("TMDB_KEY", "").strip()
MAX_NAMES, MIN_EXISTING = 12, 4

def norm(s):  # identical to build_cache.norm
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\u0640\u064b-\u065f]", "", s).replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")

def tkey(s): return re.sub(r"[^a-z0-9]+", " ", norm(s)).strip()

def get(path, **q):
    q["api_key"] = KEY
    url = "https://api.themoviedb.org/3" + path + "?" + urllib.parse.urlencode(q)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=20) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 + attempt * 2); continue
            if e.code in (401, 403): raise SystemExit("TMDB rejected the key (%s)" % e.code)
            return None
        except Exception: time.sleep(1 + attempt)
    return None

def cast_of(kind, tid):
    c = get(f"/movie/{tid}/credits" if kind == "movie" else f"/tv/{tid}/aggregate_credits")
    cast = (c or {}).get("cast", [])
    cast = sorted(cast, key=(lambda p: p.get("order", 999)) if kind == "movie" else (lambda p: -(p.get("total_episode_count") or 0)))
    return [p["name"] for p in cast[:MAX_NAMES] if p.get("name")]

def resolve(job):
    key, kind, imdb, title, year = job
    if imdb:
        f = get(f"/find/{imdb}", external_source="imdb_id") or {}
        hit = (f.get("movie_results") or f.get("tv_results") or [None])[0]
        if hit: return key, cast_of("movie" if f.get("movie_results") else "tv", hit["id"]), None
    q = {"query": title}
    if year: q["year" if kind == "movie" else "first_air_date_year"] = year
    res = (get(f"/search/{kind}", **q) or {}).get("results", [])
    want = tkey(title)
    ok = [r for r in res if want in (tkey(r.get("title") or r.get("name")), tkey(r.get("original_title") or r.get("original_name")))
          and (kind == "tv" or not year or (r.get("release_date") or "")[:4] == str(year))]
    if len(ok) == 1: return key, cast_of(kind, ok[0]["id"]), None
    return key, None, "no match" if not ok else f"{len(ok)} candidates"

def main():
    if not KEY: raise SystemExit("set TMDB_KEY")
    src = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "sheet.csv")
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    miss = json.loads(UNMATCHED.read_text(encoding="utf-8")) if UNMATCHED.exists() else {}
    jobs, seen = [], set()
    for r in csv.DictReader(open(src, encoding="utf-8-sig")):
        mt, title = r.get("Media Type"), (r.get("Title") or "").strip()
        if mt not in ("movie", "series") or not title: continue
        if re.search("[\u0600-\u06ff]", title) or "arabic" in (r.get("Source Collection") or "").lower(): continue
        n = len([a for a in re.split(r"[,،]", r.get("Actors") or "") if a.strip()])
        if n >= MIN_EXISTING: continue
        imdb = (r.get("IMDb ID") or "").strip(); imdb = imdb if re.match(r"tt\d+$", imdb) else ""
        year = (r.get("Year") or "").strip() if (r.get("Year") or "").isdigit() else ""
        if mt == "series": key, kind = "s:" + norm(title), "tv"
        else: key, kind = imdb or f"t:{norm(title)}:{year}", "movie"
        if key in cache or key in miss or key in seen: continue
        seen.add(key); jobs.append((key, kind, imdb, title, year))
    print("to fetch:", len(jobs), flush=True)
    t0 = time.time()
    with ThreadPoolExecutor(6) as ex:
        for k, (key, names, why) in enumerate(ex.map(resolve, jobs), 1):
            if names: cache[key] = names
            else: miss[key] = why or "no cast"
            if k % 100 == 0 or k == len(jobs):
                for p, d in ((CACHE, cache), (UNMATCHED, miss)):
                    tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8"); os.replace(tmp, p)
                print(k, len(jobs), int(time.time() - t0), "s", flush=True)

if __name__ == "__main__": main()
