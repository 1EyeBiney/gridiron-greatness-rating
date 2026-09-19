"""Builds the whole site into a temp directory and checks every internal
link and image resolves and every image has alt text - the same checks
used by the sibling home-field-advantage study's test_hfa_site.py."""
import re
from pathlib import Path

import pytest

import xe_site as build_site

HREF_RE = re.compile(r'href="([^"]+)"')
SRC_RE = re.compile(r'src="([^"]+)"')
IMG_TAG_RE = re.compile(r"<img\b[^>]*>")


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    build_site.render_all(out)
    return out


def _targets(html: str):
    for m in list(HREF_RE.finditer(html)) + list(SRC_RE.finditer(html)):
        url = m.group(1)
        if url.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield url.split("#")[0]


def test_every_internal_link_and_image_resolves(site):
    pages = list(site.rglob("*.html"))
    assert len(pages) >= 9
    missing = []
    for page in pages:
        html = page.read_text(encoding="utf-8")
        for url in _targets(html):
            if not url:
                continue
            target = (page.parent / url).resolve()
            if not target.is_relative_to(site.resolve()):
                continue  # the link up to the parent Gridiron Greatness site; checked by that site's own tests
            if not target.exists():
                missing.append(f"{page.relative_to(site)} -> {url}")
    assert not missing, "\n".join(missing)


def test_every_image_has_alt_text(site):
    for page in site.rglob("*.html"):
        for tag in IMG_TAG_RE.findall(page.read_text(encoding="utf-8")):
            assert 'alt="' in tag, f"{page.name}: {tag}"


def test_every_page_has_a_title_and_one_h1(site):
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert re.search(r"<title>[^<]+ · Explosive Edge</title>", html), page.name
        assert html.count("<h1>") == 1, page.name


def test_tables_have_scoped_headers(site):
    html = (site / "the-shift.html").read_text(encoding="utf-8")
    assert 'scope="col"' in html and 'scope="row"' in html
    assert "<caption>" in html


def test_data_page_lists_every_csv(site):
    data_html = (site / "data" / "index.html").read_text(encoding="utf-8")
    for csv in build_site.DATA.glob("*.csv"):
        assert csv.name in data_html
        assert (site / "data" / csv.name).exists()


def test_no_unrendered_template_placeholders(site):
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert "{{" not in html and "{%" not in html, page.name
        assert "nan" not in re.sub(r"<[^>]+>", " ", html).split(), page.name
