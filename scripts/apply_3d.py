"""Apply 3D flags from data/3d-keys.json (derived from the sheet's filename markers + tags; no filenames stored) to docs/data/movies.json.
flag = titles to mark 3D (the quality label stays, a separate 3D badge shows). unflag_quality = titles whose Quality said '3D' with no
marker or tag (not trusted): flag not set and the quality label is cleared. Run before build_collections.py."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "docs" / "data" / "movies.json"
M = json.load(open(p, encoding="utf-8")); K = json.load(open(ROOT / "data" / "3d-keys.json"))
F, U = set(K["flag"]), set(K["unflag_quality"])
for m in M:
    fl = [f for f in m["fl"] if f != "3d"]
    if m["k"] in F: fl.append("3d")
    m["fl"] = fl
    if m["k"] in U and m["q"] == "3D": m["q"] = ""
json.dump(M, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("3D flagged", sum(1 for m in M if "3d" in m["fl"]))
# rebuild collections.json (the 3D topic collection is derived from the flag) from the patched movies + stored details
import sys; sys.path.insert(0, str(ROOT / "scripts")); import build_collections
D = {}
for f in (ROOT / "docs" / "data" / "details").glob("*.json"): D.update({int(k): v for k, v in json.load(open(f, encoding="utf-8")).items()})
C = build_collections.build(M, D)
(ROOT / "docs" / "data" / "collections.json").write_text(json.dumps(C, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("collections rebuilt", {k: len(v) for k, v in C.items()})
