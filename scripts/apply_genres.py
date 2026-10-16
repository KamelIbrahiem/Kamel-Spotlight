"""One canonical (English) genre per concept: Arabic and English spellings merge (Drama = دراما). Display names are translated in the browser (i18n GEN).
Rules in data/genre-map.json; anything not listed is left exactly as is (no guessing). Patches docs/data/movies.json and statistics.json top_genres."""
import json
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
MAP = json.load(open(ROOT / "data" / "genre-map.json", encoding="utf-8"))
p = ROOT / "docs" / "data" / "movies.json"
M = json.load(open(p, encoding="utf-8")); before = Counter(g for m in M for g in m["g"])
for m in M:
    out = []
    for g in m["g"]:
        for c in MAP.get(g, [g]):
            if c not in out: out.append(c)
    m["g"] = out
json.dump(M, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
after = Counter(g for m in M for g in m["g"])
sp = ROOT / "docs" / "data" / "statistics.json"; S = json.load(open(sp, encoding="utf-8"))
S["top_genres"] = [[g, n] for g, n in after.most_common(len(S["top_genres"]))]
json.dump(S, open(sp, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("genres", len(before), "->", len(after)); print(after.most_common(12))
