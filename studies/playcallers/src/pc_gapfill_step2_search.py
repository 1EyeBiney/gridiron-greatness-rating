import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pc_wiki_fetch import _polite_get, request_count

def search(q):
    url = ("https://en.wikipedia.org/w/api.php?action=query&list=search&srnamespace=10"
           f"&srlimit=10&format=json&srsearch={q.replace(' ', '%20')}")
    resp = _polite_get(url)
    data = resp.json()
    for hit in data.get("query", {}).get("search", []):
        print(hit["title"])

for q in ["New England Patriots offensive coordinator", "Dallas Cowboys defensive coordinator",
          "Arizona Cardinals offensive coordinators navbox"]:
    print("=== ", q)
    search(q)
print("requests used:", request_count())
