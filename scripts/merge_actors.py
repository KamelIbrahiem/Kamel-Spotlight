"""docs/data/actors.json from data/actors-wiki.json (bio + Commons photo) and the workbook 'Actor Photos' tab (data/actor-photos.json, takes priority)."""
import json
from pathlib import Path
R = Path(__file__).resolve().parent.parent
w = json.loads((R / "data/actors-wiki.json").read_text(encoding="utf-8")) if (R / "data/actors-wiki.json").exists() else {}
ph = json.loads((R / "data/actor-photos.json").read_text(encoding="utf-8")) if (R / "data/actor-photos.json").exists() else {}
tm = json.loads((R / "data/actor-tmdb.json").read_text(encoding="utf-8")) if (R / "data/actor-tmdb.json").exists() else {}
hold = json.loads((R / "data/actors-wiki-hold.json").read_text(encoding="utf-8")) if (R / "data/actors-wiki-hold.json").exists() else {}
out = {}
for n, r in w.items():
    if n in hold: continue   # identity not certain: keep out of the site
    from urllib.parse import quote
    out[n] = {"b": r["b"], "l": r["l"], "u": f"https://{r['l']}.wikipedia.org/wiki/" + quote(r["t"].replace(" ", "_"))}
    if r.get("i"): out[n].update(i=r["i"], s="wikipedia")
for n, p in tm.items():   # TMDB profile (path) - verified through shared film credits
    out.setdefault(n, {}).update(i="https://image.tmdb.org/t/p/w342" + p, s="tmdb")
for n, p in ph.items():
    out.setdefault(n, {}).update(i=p["url"], s="workbook", cr=p["credit"])
man = json.loads((R / "data/actors-manual.json").read_text(encoding="utf-8")) if (R / "data/actors-manual.json").exists() else {}   # bios the owner supplied himself
for n, e in man.items(): out.setdefault(n, {}).update(e)
(R / "docs/data/actors.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("actors.json", len(out), "bios", sum("b" in v for v in out.values()), "photos", sum("i" in v for v in out.values()))
