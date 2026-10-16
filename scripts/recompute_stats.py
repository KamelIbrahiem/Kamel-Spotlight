"""Recompute docs/data/statistics.json from docs/data/movies.json (hidden duplicates m.hd excluded)."""
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sp = R / "docs/data/statistics.json"
S = json.loads(sp.read_text(encoding="utf-8"))
M = [m for m in json.loads((R / "docs/data/movies.json").read_text(encoding="utf-8")) if not m.get("hd")]
act, dr = defaultdict(set), defaultdict(set)
for m in M:
    for a in m["a"]: act[a].add(m["id"])
    for d in m["d"]: dr[d].add(m["id"])
S.update(total=len(M), by_type=dict(Counter(m["c"] for m in M)),
         top_genres=Counter(g for m in M for g in m["g"]).most_common(15),
         top_actors=sorted(((a, len(v)) for a, v in act.items()), key=lambda x: -x[1])[:15],
         top_directors=sorted(((a, len(v)) for a, v in dr.items()), key=lambda x: -x[1])[:15],
         countries=Counter(c for m in M for c in m["co"]).most_common(12),
         decades=sorted(Counter(f"{m['y']//10*10}s" for m in M if m["y"]).items()),
         ratings=sorted(Counter(int(m["r"]) for m in M if m["r"]).items()),
         qualities=Counter(m["q"] or "?" for m in M).most_common(8), built=date.today().isoformat())
if __name__ == "__main__":
    import sys
    if "--dry" in sys.argv: print(json.dumps({k: S[k] for k in ("total", "by_type", "top_genres", "top_actors", "decades", "qualities")}, ensure_ascii=False)); raise SystemExit
    sp.write_text(json.dumps(S, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"); print("total", S["total"], S["by_type"])
