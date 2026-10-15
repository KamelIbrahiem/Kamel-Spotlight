"""TMDB profile photos for actors with 3+ library titles. Verified by film: a name is taken only from the cast list of a library film
(matched by IMDb ID), so a photo always belongs to a person credited on one of that actor's own films. Resumable.
Usage: TMDB_KEY=<v3 key> python3 scripts/fetch_actor_photos.py      Output: data/actor-tmdb.json {name: "/profile_path.jpg"}, data/actor-tmdb-done.json
The key is read from the environment only and never written."""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
R = Path(__file__).resolve().parent.parent
KEY = os.environ.get("TMDB_KEY", "").strip()
def get(path, **q):
    q["api_key"] = KEY
    for a in range(4):
        try:
            with urllib.request.urlopen("https://api.themoviedb.org/3" + path + "?" + urllib.parse.urlencode(q), timeout=20) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(2 + 2 * a); continue
            if e.code in (401, 403): raise SystemExit("key rejected")
            return None
        except Exception: time.sleep(1 + a)
def main():
    if not KEY: raise SystemExit("set TMDB_KEY")
    M = json.load(open(R / "docs/data/movies.json"))
    cnt = Counter(a for m in M for a in m["a"]); want = {a for a, n in cnt.items() if n >= 3}
    OUT, DONE = R / "data/actor-tmdb.json", R / "data/actor-tmdb-done.json"
    res = json.loads(OUT.read_text()) if OUT.exists() else {}; done = set(json.loads(DONE.read_text())) if DONE.exists() else set()
    films = [m for m in M if m["k"].startswith("tt") and m["k"] not in done and any(a in want and a not in res for a in m["a"])]
    print("films to read:", len(films), flush=True)
    def one(m):
        f = get(f"/find/{m['k']}", external_source="imdb_id") or {}
        hit = (f.get("movie_results") or f.get("tv_results") or [None])[0]
        if not hit: return m["k"], {}
        c = get(f"/movie/{hit['id']}/credits" if f.get("movie_results") else f"/tv/{hit['id']}/aggregate_credits") or {}
        return m["k"], {p["name"]: p["profile_path"] for p in c.get("cast", []) if p.get("profile_path") and p.get("name") in want}
    with ThreadPoolExecutor(8) as ex:
        for i, (k, d) in enumerate(ex.map(one, films)):
            for n, pp in d.items(): res.setdefault(n, pp)
            done.add(k)
            if i % 300 == 299: OUT.write_text(json.dumps(res, ensure_ascii=False)); DONE.write_text(json.dumps(sorted(done))); print(i + 1, len(res), flush=True)
    OUT.write_text(json.dumps(res, ensure_ascii=False)); DONE.write_text(json.dumps(sorted(done))); print("photos", len(res), "of", len(want))
if __name__ == "__main__": main()
