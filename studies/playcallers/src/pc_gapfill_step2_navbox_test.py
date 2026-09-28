import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pc_wiki_fetch import fetch_wikitext, request_count

tests = [
    "Template:New England Patriots offensive coordinator navbox",
    "Template:Dallas Cowboys defensive coordinator navbox",
    "Template:Arizona Cardinals offensive coordinators",
    "Template:Arizona Cardinals defensive coordinators",
]
for t in tests:
    r = fetch_wikitext(t)
    print(t, "->", "FOUND" if r else "404")
    if r:
        print(r[0][:500])
        print("...")
print("requests used:", request_count())
