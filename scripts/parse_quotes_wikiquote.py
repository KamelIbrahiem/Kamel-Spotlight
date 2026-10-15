"""Parse cached English Wikiquote pages (fetch_quotes_wikiquote.py) into data/quotes-foreign.json.
Strict: a page is used only when it carries the same IMDb id as our title ({{IMDb title|id=...}}). Max 1 short one-line quotes per film."""
import json, re, urllib.parse
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SKIP = re.compile(r"about|tagline|cast|see also|external|dialogue|trivia|reference|further|taglines|sources|gallery|credits|plot|synopsis|sequel", re.I)

def clean(s):
    s = re.sub(r"''\s*\[[^\]]*\]\s*''", "", s)            # stage directions
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = re.sub(r"<ref.*?(</ref>|/>)", "", s); s = re.sub(r"<[^>]+>", "", s)
    s = s.replace("'''", "").replace("''", "")
    return re.sub(r"\s+", " ", s).strip()

BAD = re.compile(r"fuck|shit|bitch|cunt|dick|cock|pussy|asshole|bastard|slut|whore|nigg|fag|rape|sex|penis|damn|\\bass\\b|piss|krauts?|retard|negro|jap\\b|kill yourself", re.I)

def good(q):
    """Keep short, clean, complete one-line quotes: no strong language, no lyric run-ons, ends like a sentence."""
    return (25 <= len(q) <= 200 and not BAD.search(q) and not re.search(r"[a-z][,.!?][A-Za-z]", q)
            and q[-1] in '.!?"\u201d\u2019' and not q.endswith("...") and "..." not in q[:4] and q.count(" ") >= 4)

def imdb(text):
    m = re.search(r"\{\{\s*IMDb title\s*\|\s*(?:id\s*=\s*)?(\d{6,8})", text, re.I)
    return "tt" + m.group(1).zfill(7) if m else None

def quotes(text):
    out, sec = [], ""
    for ln in text.split("\n"):
        h = re.match(r"^==+\s*([^=]+?)\s*==+\s*$", ln)
        if h: sec = h.group(1); continue
        if re.search(r"\{\{\s*(center|spoiler)", ln, re.I) and not ln.startswith("*"): continue
        if not ln.startswith("*") or ln.startswith("**") or SKIP.search(sec) and sec: continue
        if sec == "" : continue
        q = clean(ln.lstrip("* "))
        if not (15 <= len(q) <= 220) or re.search(r"[\[\]{}|<>=]", q) or q.count('"') % 2 or q.isupper(): continue
        who = clean(sec) if not re.search(r"^(quotes?|dialogue)$", sec, re.I) else ""
        if good(q): out.append({"q": q, "who": who})
    return out

def main():
    raw = json.loads((ROOT / "tmp_quotes" / "raw.json").read_text(encoding="utf-8"))
    movies = json.load(open(ROOT / "docs" / "data" / "movies.json", encoding="utf-8"))
    res = {}; seen = set()
    for m in movies:
        if m["c"] != "movie" or not m["y"] or not m["k"].startswith("tt"): continue
        for t in (f'{m["t"]} ({m["y"]} film)', m["t"]):
            p = raw.get(t)
            if not p or imdb(p["text"]) != m["k"]: continue
            qs = quotes(p["text"])[:1]
            if qs:
                url = "https://en.wikiquote.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"), safe="_(),!'")
                res[m["k"]] = [{"q": x["q"], "lang": "en", "who": x["who"], "src": [["Wikiquote", url]]} for x in qs]
            break
    (ROOT / "data" / "quotes-foreign.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("films:", len(res), "quotes:", sum(len(v) for v in res.values()))
if __name__ == "__main__": main()
