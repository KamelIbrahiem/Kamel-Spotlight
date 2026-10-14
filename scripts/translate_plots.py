"""Machine-translate English-only plots to Arabic (offline, Argos Translate). Resumable.
Usage: python3 scripts/translate_plots.py [csv]   (needs: pip install argostranslate; model en->ar is downloaded on first run)
Cache: data/plot-ar.json  {sha1(plot): arabic}. The website shows these with the label "ترجمة آلية".
Plots that already contain Arabic are never translated. Only plots are read; nothing else leaves the CSV."""
import csv, hashlib, json, re, sys, os, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "plot-ar.json"

def key(p): return hashlib.sha1(p.strip().encode("utf-8")).hexdigest()[:16]

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "data" / "sheet.csv")
    rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
    todo, seen = [], set()
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    for r in rows:
        p = (r.get("Plot") or "").strip()
        if p and not re.search("[\u0600-\u06ff]", p) and key(p) not in cache and key(p) not in seen:
            seen.add(key(p)); todo.append(p)
    print("to translate:", len(todo), flush=True)
    if not todo: return
    import argostranslate.package as ap, argostranslate.translate as at
    if not any(l.code == "ar" for l in at.get_installed_languages()):
        ap.update_package_index()
        pk = next(x for x in ap.get_available_packages() if x.from_code == "en" and x.to_code == "ar")
        ap.install_from_path(pk.download())
    t0 = time.time()
    for i, p in enumerate(todo, 1):
        try: cache[key(p)] = at.translate(p, "en", "ar")
        except Exception as e: print("skip", e); continue
        if i % 25 == 0 or i == len(todo):
            tmp = CACHE.with_suffix(".tmp"); tmp.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8"); os.replace(tmp, CACHE)
            print(i, len(todo), int(time.time() - t0), "s", flush=True)

if __name__ == "__main__": main()
