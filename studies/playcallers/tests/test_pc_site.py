"""Builds the whole site into a temp directory and checks every internal
link and image resolves, structural accessibility invariants hold, and no
"nan"/"None" leaked into rendered text - the same checks used by the
sibling explosive-edge study's test_xe_site.py."""
import re

import pytest

import pc_site as build_site

HREF_RE = re.compile(r'href="([^"]+)"')
SRC_RE = re.compile(r'src="([^"]+)"')
IMG_TAG_RE = re.compile(r"<img\b[^>]*>")
H1_RE = re.compile(r"<h1[ >]")

STUDIES_BAR_LINKS = [
    "../index.html", "../rating.html", "../home-field-advantage/index.html",
    "../explosive-edge/index.html", "../playcallers/index.html", "../how-it-was-made.html",
]


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
    external = []
    for page in pages:
        html = page.read_text(encoding="utf-8")
        for url in _targets(html):
            if not url:
                continue
            if url.startswith("../"):
                external.append(f"{page.relative_to(site)} -> {url}")
                continue
            target = (page.parent / url).resolve()
            if not target.is_relative_to(site.resolve()):
                external.append(f"{page.relative_to(site)} -> {url}")
                continue
            if not target.exists():
                missing.append(f"{page.relative_to(site)} -> {url}")
    assert not missing, "\n".join(missing)
    # external (studies-bar) links are reported, not checked - they point
    # outside this study's own tmp render and are covered by the main
    # site's own build.
    print(f"external links skipped: {len(external)}")


def test_every_image_has_alt_text(site):
    for page in site.rglob("*.html"):
        for tag in IMG_TAG_RE.findall(page.read_text(encoding="utf-8")):
            assert 'alt="' in tag, f"{page.name}: {tag}"


def test_every_page_has_a_title_and_one_h1(site):
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert re.search(r"<title>[^<]+ · The Playcallers</title>", html), page.name
        assert len(H1_RE.findall(html)) == 1, page.name


def test_tables_have_captions_and_scoped_headers(site):
    checked = 0
    for page in site.rglob("*.html"):
        if page.parent.name == "data":
            continue
        html = page.read_text(encoding="utf-8")
        if "<table>" not in html:
            continue
        assert 'scope="col"' in html, page.name
        assert 'scope="row"' in html, page.name
        assert "<caption>" in html, page.name
        checked += 1
    assert checked >= 6


def test_studies_bar_present_with_one_current_link_on_every_page(site):
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert 'class="studies-bar"' in html, page.name
        assert html.count('aria-current="page"') == 1, page.name
        for link in STUDIES_BAR_LINKS:
            assert link in html, f"{page.name} missing studies-bar link {link}"


def test_data_page_lists_every_csv(site):
    data_html = (site / "data" / "index.html").read_text(encoding="utf-8")
    for csv in build_site.DATA.glob("*.csv"):
        assert csv.name in data_html
        assert (site / "data" / csv.name).exists()


def test_no_unrendered_template_placeholders_and_no_nan_or_none(site):
    for page in site.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert "{{" not in html and "{%" not in html, page.name
        text = re.sub(r"<[^>]+>", " ", html)
        words = text.split()
        assert "nan" not in words, page.name
        assert "None" not in words, page.name


def test_who_called_plays_has_32_franchise_tables_and_jump_list(site):
    html = (site / "who-called-plays.html").read_text(encoding="utf-8")
    assert html.count("<table>") == 32
    assert 'class="jump-list"' in html
