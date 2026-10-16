"""Fill missing posters from data/poster-fill.json {key: elCinema poster url}. Each entry was accepted only when the elCinema work page title matched
the title (normalised) AND the year exactly. Titles that do not match stay blank. Patches docs/data/movies.json and the health report."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
F = json.load(open(ROOT / "data" / "poster-fill.json", encoding="utf-8"))
p = ROOT / "docs" / "data" / "movies.json"; M = json.load(open(p, encoding="utf-8")); n = 0
for m in M:
    if not m["p"] and m["k"] in F: m["p"] = F[m["k"]]; n += 1
json.dump(M, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
hp = ROOT / "docs" / "data" / "health.json"; H = json.load(open(hp, encoding="utf-8"))
k = next((x for x in H if "poster" in x.lower()), None)
if k: H[k] = [i for i in H[k] if not M[i]["p"]]
json.dump(H, open(hp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("posters filled", n, "still missing", sum(1 for m in M if not m["p"]), "health key", k, len(H.get(k, [])) if k else "")
