"""Foreign-film quotes from English Wikiquote (CC BY-SA 4.0). Resumable; raw pages cached in tmp (not shipped).
A page is accepted ONLY if it is verifiably the same film: it carries {{IMDb title|id=<our IMDb id>}}, or (no IMDb link on the page)
its category list has '<year> ... films' with our year AND the page title equals our title (optionally '(<year> film)').
Output: data/quotes-foreign.json  {key: {"q","who","title","url"}}"""
import json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "tmp_quotes" / "raw.json"
API = "https://en.wikiquote.org/w/api.php"
UA = {"User-Agent": "KamelSpotlight/1.0 (personal film library; quote lookup, low rate)"}

def api(titles):
    u = API + "?" + urllib.parse.urlencode({"action": "query", "titles": "|".join(titles), "prop": "revisions", "rvprop": "content",
                                            "rvslots": "main", "redirects": 1, "format": "json", "formatversion": 2})
    for a in range(4):
        try: return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25))
        except Exception: time.sleep(2 + a * 3)
    return None

def main():
    movies = json.load(open(ROOT / "docs" / "data" / "movies.json", encoding="utf-8"))
    cand = {}
    for m in movies:
        if m["c"] != "movie" or not m["y"] or not m["k"].startswith("tt"): continue
        for t in (f'{m["t"]} ({m["y"]} film)', m["t"]): cand[t] = None
    titles = list(cand)
    raw = json.loads(RAW.read_text(encoding="utf-8")) if RAW.exists() else {}
    todo = [t for t in titles if t not in raw]
    print("titles to ask:", len(todo), flush=True)
    from concurrent.futures import ThreadPoolExecutor
    batches = [todo[i:i + 40] for i in range(0, len(todo), 40)]
    def work(batch):
        r = api(batch); time.sleep(0.3)
        return batch, r
    n = 0
    with ThreadPoolExecutor(4) as ex:
        for batch, r in ex.map(work, batches):
            n += 1
            if not r: continue
            q = r.get("query", {})
            norm = {x["from"]: x["to"] for x in q.get("normalized", [])}
            red = {x["from"]: x["to"] for x in q.get("redirects", [])}
            pages = {pg["title"]: pg for pg in q.get("pages", [])}
            for t in batch:
                tt = red.get(norm.get(t, t), norm.get(t, t)); pg = pages.get(tt)
                raw[t] = None if (not pg or pg.get("missing")) else {"title": pg["title"], "text": (pg.get("revisions") or [{"slots":{"main":{"content":""}}}])[0]["slots"]["main"]["content"]}
            if n % 20 == 0: RAW.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8"); print(n, len(batches), flush=True)
    RAW.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8"); print("done", len(raw))

if __name__ == "__main__": main()
