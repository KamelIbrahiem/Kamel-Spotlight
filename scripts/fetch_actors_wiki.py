"""Actor bios + free photos from Wikipedia (Arabic names -> ar.wikipedia, others -> en.wikipedia). Resumable, no API key.
A page is accepted only if (1) its title is the exact actor name (after redirect), (2) it is not a disambiguation page, (3) its short
description names a film/TV/stage profession, and (4) its wikitext mentions at least one title from this library (filmography check).
Output: data/actors-wiki.json {name: {l, t, b, i?}}  b = intro (<= 3 sentences), t = page title, l = language, i = commons image URL.
Photos are kept only when they come from Wikimedia Commons (free licence); non-free local uploads are dropped."""
import json, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from collections import Counter, defaultdict
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "actors-wiki.json"
MISS = ROOT / "data" / "actors-wiki-miss.json"
UA = "KamelSpotlight/1.0 (personal film library; contact via github KamelIbrahiem)"
PROF = re.compile(r"actor|actress|comedian|filmmaker|film director|director|screenwriter|voice|performer|presenter|singer|television|film|stage|theat|model|producer|ممثل|مخرج|مغني|مطرب|كوميدي|مقدم|سينم|مسرح|تلفزيون|تليفزيون|منتج|كاتب|فنان|مذيع", re.I)
def fold(s):
    s = unicodedata.normalize("NFKD", (s or "").lower()); s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[\u0640\u064b-\u065f]", "", s)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"), ("ة", "ه")): s = s.replace(a, b)
    return re.sub(r"[^a-z0-9\u0600-\u06ff]+", " ", s).strip()
def api(lang, **q):
    q.update(format="json", formatversion="2", redirects="1")
    url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(q)
    for a in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            time.sleep(int(e.headers.get('Retry-After') or 0) or (30 + a * 30) if e.code == 429 else 2 + a * 3)
        except Exception as e:
            time.sleep(2 + a * 3)
    return None
def main():
    M = json.load(open(ROOT / "docs/data/movies.json"))
    cnt, films, lead = Counter(), defaultdict(set), Counter()
    for m in M:
        for i, a in enumerate(m["a"]):
            cnt[a] += 1; films[a].add(m["t"])
            if i < 3: lead[a] += 1   # top-billed (first three) credits
    names = sorted([a for a, n in cnt.items() if n >= 3], key=lambda a: (-lead[a], -cnt[a]))   # lead-role stars first, then most titles
    res = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    miss = json.loads(MISS.read_text(encoding="utf-8")) if MISS.exists() else {}
    todo = [n for n in names if n not in res and n not in miss]
    if len(sys.argv) > 2: todo = [n for n in todo if bool(re.search("[\u0600-\u06ff]", n)) == (sys.argv[2] == "ar")]
    if len(sys.argv) > 1: todo = todo[: int(sys.argv[1])]
    print("actors 3+:", len(names), "todo:", len(todo), flush=True)
    SUF = {"ar": [" (ممثل)", " (ممثلة)"], "en": [" (actor)", " (actress)"]}
    def process(lang, qmap):
        """qmap: {query title: actor name}. Returns {actor: page} for pages passing checks; records misses."""
        d = api(lang, action="query", titles="|".join(qmap), prop="pageprops|description|extracts|pageimages", exintro="1", explaintext="1", exsentences="3", exlimit="20", piprop="original", ppprop="disambiguation")
        if not d: return None
        q = d.get("query", {}); back = {}
        for x in q.get("normalized", []) + q.get("redirects", []): back[x["to"]] = x["from"]
        out = {}
        for p in q.get("pages", []):
            if p.get("missing") or "invalid" in p: continue
            src = p["title"]
            while src in back: src = back[src]
            nm = qmap.get(src)
            if not nm: continue
            if "disambiguation" in (p.get("pageprops") or {}): miss.setdefault(nm, "disambiguation"); continue
            if not PROF.search(p.get("description") or ""): miss.setdefault(nm, "not a screen/stage profession: " + (p.get("description") or "")[:60]); continue
            redirected = src != p["title"]
            plain = fold(re.sub(r"\s*\(.*?\)$", "", p["title"])).replace(" ", "")
            if not redirected and plain != fold(nm).replace(" ", ""): miss.setdefault(nm, "title differs: " + p["title"]); continue
            out[nm] = p
        return out
    def verify(lang, cand):
        items = list(cand.items())
        for j in range(0, len(items), 10):
            sub = items[j:j + 10]
            w = api(lang, action="query", titles="|".join(p["title"] for _, p in sub), prop="revisions", rvprop="content", rvslots="main")
            txt = {}
            for p in (w or {}).get("query", {}).get("pages", []):
                try: txt[p["title"]] = fold(p["revisions"][0]["slots"]["main"]["content"])
                except Exception: pass
            for nm, p in sub:
                t = txt.get(p["title"])
                if t is None: miss[nm] = "wikitext unavailable"; continue
                hit = [f for f in films[nm] if len(fold(f)) >= 5 and re.search(r"(?<![a-z0-9\u0600-\u06ff])" + re.escape(fold(f)) + r"(?![a-z0-9\u0600-\u06ff])", t)]
                if not hit: miss[nm] = "no library film found on page"; continue
                img = ((p.get("original") or {}).get("source", "")).split("?")[0]
                rec = {"l": lang, "t": p["title"], "b": (p.get("extract") or "").strip(), "n": len(hit)}
                if "/wikipedia/commons/" in img: rec["i"] = img
                if rec["b"]: res[nm] = rec; miss.pop(nm, None)
                else: miss[nm] = "empty intro"
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock(); done = [0]
    def run(lang, batch):
        cand = process(lang, {n: n for n in batch})
        if cand is None: return
        for nm in batch:
            if nm not in cand and nm not in miss: miss[nm] = "no page"
        verify(lang, cand)
        retry = [n for n in batch if n not in res and (miss.get(n, "").startswith(("disambig", "not a screen", "no page", "no library")))]
        if retry:
            qm = {n + s: n for n in retry for s in SUF[lang]}
            for k in range(0, len(qm), 20):
                c2 = process(lang, dict(list(qm.items())[k:k + 20]))
                if c2: verify(lang, {n: p for n, p in c2.items() if n not in res})
        with lock:
            done[0] += len(batch)
            OUT.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8"); MISS.write_text(json.dumps(miss, ensure_ascii=False), encoding="utf-8")
            print(lang, done[0], "done, accepted", len(res), flush=True)
    ar_g = [n for n in todo if re.search("[\u0600-\u06ff]", n)]; en_g = [n for n in todo if not re.search("[\u0600-\u06ff]", n)]
    jobs = []
    for i in range(0, max(len(ar_g), len(en_g)), 20):   # interleave Arabic and English batches so both lists advance by priority
        if ar_g[i:i + 20]: jobs.append(("ar", ar_g[i:i + 20]))
        if en_g[i:i + 20]: jobs.append(("en", en_g[i:i + 20]))
    with ThreadPoolExecutor(1) as ex: list(ex.map(lambda j: run(*j), jobs))
if __name__ == "__main__": main()
