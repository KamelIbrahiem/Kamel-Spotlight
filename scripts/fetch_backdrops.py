"""Fetch one TMDB backdrop path per title that has an IMDb ID. Resumable, polite (6 threads, backs off on 429).
Usage:  TMDB_KEY=<v3 api key> python3 scripts/fetch_backdrops.py [imdb-ids.txt | csv]   (default: data/sheet.csv; the .txt has one IMDb ID per line)
Cache: data/backdrop-tmdb.json  {imdb_id: "/abc.jpg" | ""}   ("" = TMDB has no backdrop; not retried)
The site shows https://image.tmdb.org/t/p/w1280<path>. The key is read from the environment only and is never written anywhere."""
import csv, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "backdrop-tmdb.json"
KEY = os.environ.get("TMDB_KEY", "").strip()

def find(imdb):
    url = f"https://api.themoviedb.org/3/find/{imdb}?" + urllib.parse.urlencode({"api_key": KEY, "external_source": "imdb_id"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=20) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 + attempt * 2); continue
            if e.code in (401, 403): raise SystemExit("TMDB rejected the key (%s)" % e.code)
            return None
        except Exception: time.sleep(1 + attempt)
    return None

def one(imdb):
    f = find(imdb)
    if f is None: return imdb, None            # transient failure: retry next run
    hits = (f.get("movie_results") or []) + (f.get("tv_results") or [])
    paths = [h.get("backdrop_path") for h in hits if h.get("backdrop_path")]
    return imdb, (paths[0] if paths else "")

def main():
    if not KEY: raise SystemExit("set TMDB_KEY")
    src = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "sheet.csv")
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    ids = []
    if src.endswith(".txt"):
        cand = [l.strip() for l in open(src, encoding="utf-8")]
    else:
        cand = [(r.get("IMDb ID") or "").strip() for r in csv.DictReader(open(src, encoding="utf-8-sig"))]
    for i in cand:
        if re.match(r"tt\d+$", i) and i not in cache and i not in ids: ids.append(i)
    print("to fetch:", len(ids), "already cached:", len(cache), flush=True)
    done = 0
    with ThreadPoolExecutor(6) as ex:
        for imdb, p in ex.map(one, ids):
            if p is not None: cache[imdb] = p
            done += 1
            if done % 200 == 0:
                CACHE.write_text(json.dumps(cache), encoding="utf-8"); print(done, "/", len(ids), flush=True)
    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    print("done. with backdrop:", sum(1 for v in cache.values() if v), "none:", sum(1 for v in cache.values() if not v))

if __name__ == "__main__": main()
