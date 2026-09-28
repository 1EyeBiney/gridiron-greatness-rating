"""Shared polite Wikipedia fetch/cache helper for The Playcallers, Phase 0.

One request per second at most; every fetched page cached under
data/raw/wikipedia/ (gitignored) so re-runs don't re-hit the network.
Copied from old-gold-standard/src/wiki_fetch.py with RAW_DIR/User-Agent
adjusted, plus support for fetching raw wikitext (action=raw) instead of
rendered HTML, which is what pc_extract_staff.py actually parses.
"""
import hashlib
import pathlib
import time

import requests

RAW_DIR = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw" / "wikipedia"
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "GridironGreatness-research/1.0 (1eyebiney@gmail.com; "
    "non-commercial research project)"
}

REQUEST_LOG = RAW_DIR.parent / "wikipedia_request_log.txt"

_last_request_time = [0.0]
_request_count = [0]


def _cache_path(title: str, kind: str) -> pathlib.Path:
    h = hashlib.sha1(title.encode("utf-8")).hexdigest()[:16]
    safe = "".join(c if c.isalnum() else "_" for c in title)[:80]
    ext = "wikitext" if kind == "raw" else "html"
    return RAW_DIR / f"{safe}_{h}.{ext}"


def _polite_get(url: str) -> requests.Response:
    elapsed = time.time() - _last_request_time[0]
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.encoding = "utf-8"  # Wikipedia serves UTF-8; don't let requests guess wrong
    _last_request_time[0] = time.time()
    _request_count[0] += 1
    with open(REQUEST_LOG, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{resp.status_code}\t{url}\n")
    return resp


def fetch_wikipedia(title: str, lang: str = "en") -> tuple[str, str] | None:
    """Fetch a Wikipedia article's rendered HTML by exact title.

    Returns (html_text, canonical_url) or None if the page does not exist
    (404). Caches to disk; only hits the network for uncached titles, and
    sleeps to stay at <=1 request/sec when it does.
    """
    cache = _cache_path(title, "html")
    url = f"https://{lang}.wikipedia.org/wiki/" + title.replace(" ", "_")
    if cache.exists():
        text = cache.read_text(encoding="utf-8")
        if text == "__404__":
            return None
        return text, url

    resp = _polite_get(url)
    if resp.status_code == 404:
        cache.write_text("__404__", encoding="utf-8")
        return None
    resp.raise_for_status()
    cache.write_text(resp.text, encoding="utf-8")
    return resp.text, url


def fetch_wikitext(title: str, lang: str = "en") -> tuple[str, str] | None:
    """Fetch a Wikipedia article's raw wikitext via action=raw.

    Returns (wikitext, canonical_url) or None if the page does not exist.
    Cached separately from the rendered HTML. The canonical_url returned is
    the normal /wiki/ URL (for citation), not the ?action=raw URL fetched.
    """
    cache = _cache_path(title, "raw")
    display_url = f"https://{lang}.wikipedia.org/wiki/" + title.replace(" ", "_")
    fetch_url = f"https://{lang}.wikipedia.org/w/index.php?title=" + title.replace(" ", "_") + "&action=raw"
    if cache.exists():
        text = cache.read_text(encoding="utf-8")
        if text == "__404__":
            return None
        return text, display_url

    resp = _polite_get(fetch_url)
    if resp.status_code == 404:
        cache.write_text("__404__", encoding="utf-8")
        return None
    resp.raise_for_status()
    cache.write_text(resp.text, encoding="utf-8")
    return resp.text, display_url


def request_count() -> int:
    return _request_count[0]
