"""Foreign quotes: only AFI's 100 Movie Quotes lines that (1) appear on afi.com's list page, (2) appear verbatim on the film's Wikiquote page,
(3) belong to a film (title+year) in the library. Two independent sources are cited per quote. Writes data/quotes-foreign.json {imdb: [..]}."""
import re, json, html, unicodedata, urllib.request, urllib.parse, time
from pathlib import Path
R = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 KamelSpotlight/1.0 (personal film library)"}
def get(u):
    for a in range(5):
        try: return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=40).read().decode("utf8", "ignore")
        except Exception as e: time.sleep(3 + 4 * a)
def f(s):
    s = html.unescape(s).replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
    s = unicodedata.normalize("NFKD", s.lower()); return re.sub(r"[^a-z0-9]+", " ", s).strip()
wt = json.loads(get("https://en.wikipedia.org/w/api.php?action=parse&page=AFI%27s_100_Years...100_Movie_Quotes&prop=wikitext&format=json&formatversion=2"))["parse"]["wikitext"]
site = f(re.sub(r"<[^>]+>", " ", get("https://www.afi.com/afis-100-years-100-movie-quotes/")))
tab = wt[wt.index('{| class="wikitable'):]
tab = re.sub(r"<!--.*?-->", "", tab, flags=re.S); tab = re.sub(r"\{\{efn[^{}]*(?:\{\{[^{}]*\}\}[^{}]*)*\}\}", "", tab, flags=re.S); tab = re.sub(r"<ref.*?</ref>", "", tab, flags=re.S)
tab = re.sub(r"\{\{sortname\|([^|}]*)\|([^|}]*)(?:\|([^}]*))?\}\}", lambda m: m.group(3) or (m.group(1) + " " + m.group(2)), tab)
def clean(c):
    c = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", c); c = re.sub(r"''+", "", c); return c.strip().lstrip("|").strip()
Q = []
for r in tab.split("\n|-")[1:]:
    cells = [clean(x) for x in re.split(r"\n\|", r.strip("\n")) if clean(x)]
    cells = [c for c in cells if not c.startswith("!")]
    if len(cells) >= 6 and cells[0].isdigit():
        film = re.sub(r"\s*\((?:\d{4} )?film\)$", "", cells[4]); Q.append(dict(rank=int(cells[0]), q=cells[1].strip(' "'), ch=cells[2], film=film, yr=cells[5][:4]))
M = json.load(open(R / "docs/data/movies.json")); det = {}
lib = {(f(m["t"]), str(m["y"])): m for m in M if m["c"] in ("movie", "arabic-movie")}
out, log = {}, []
for x in Q:
    m = lib.get((f(x["film"]), x["yr"]))
    if not m: log.append((x["rank"], x["film"], "not in library")); continue
    qn = f(x["q"].rstrip(".!?"))
    if qn not in site: log.append((x["rank"], x["film"], "not found on afi.com")); continue
    slug = urllib.parse.quote(re.sub(r"\s*\(.*\)$", "", x["film"]).replace(" ", "_"))
    wq = None
    for cand in (slug, slug + "_(film)", slug + "_(" + x["yr"] + "_film)"):
        j = get("https://en.wikiquote.org/w/api.php?action=parse&redirects=1&prop=text&format=json&formatversion=2&page=" + cand)
        try: txt = json.loads(j)["parse"]["text"]
        except Exception: continue
        if "To get this to work" in txt and False: pass
        page = f(re.sub(r"<[^>]+>", " ", txt)); time.sleep(1.2)
        if qn in page: wq = "https://en.wikiquote.org/wiki/" + cand; break
    if not wq: log.append((x["rank"], x["film"], "not verbatim on Wikiquote")); continue
    imdb = None
    out.setdefault(m["k"], []).append({"q": x["q"], "lang": "en", "who": x["ch"], "src": [["AFI's 100 Years...100 Movie Quotes", "https://www.afi.com/afis-100-years-100-movie-quotes/"], ["Wikiquote", wq]], "film": m["t"], "y": m["y"], "rank": x["rank"]})
    print("OK", x["rank"], m["t"], flush=True)
(R / "data/quotes-foreign.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(Q), "afi rows;", sum(len(v) for v in out.values()), "verified"); [print(l) for l in log]
