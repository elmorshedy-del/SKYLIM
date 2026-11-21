"""Search guarantees for every public page, from Google Search Central guidance (docs/SEO-PLAN.md §1).

Rendering checks need no database; the serving checks use the app client.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser

import pytest

import data
import landing_pages
from app.domain import pricing
from app.domain.catalog import get_catalog
from marketing import page as site, seo

ALLOWED = {k for k, v in data.OPERATIONS["authority"].items() if v}
BANNED = [w.strip().lower() for w in re.search(r"Never: ([^.]+)\.", data.VOICE["tone"]).group(1).split(",")]
KNOWN = {"/", "/terms", "/privacy", "/accessibility", "/pricing.md"} | set(landing_pages.BY_PATH)


class Doc(HTMLParser):
    """Collects what a crawler reads: head metadata, headings, structured data, links, visible text."""

    def __init__(self, html: str):
        super().__init__()
        self.title = self.description = self.canonical = None
        self.h1s, self.ld, self.hrefs, self.text = [], [], [], []
        self._stack, self._buf = [], None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self._stack.append(tag)
        if tag == "meta" and a.get("name") == "description":
            self.description = a["content"]
        elif tag == "link" and a.get("rel") == "canonical":
            self.canonical = a["href"]
        elif tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])
        elif tag in ("h1", "title") or (tag == "script" and a.get("type") == "application/ld+json"):
            self._buf = (tag, [])
        if tag in ("meta", "link", "input", "br", "img"):
            self._stack.pop()

    def handle_endtag(self, tag):
        if self._buf and self._buf[0] == tag:
            content = "".join(self._buf[1])
            if tag == "h1":
                self.h1s.append(" ".join(content.split()))
            elif tag == "title" and self.title is None and "head" in self._stack:
                self.title = content
            elif tag == "script":
                self.ld.append(json.loads(content))
            self._buf = None
        if self._stack and self._stack[-1] == tag:
            self._stack.pop()

    def handle_data(self, d):
        if self._buf:
            self._buf[1].append(d)
        if not {"head", "script", "style", "select", "svg"} & set(self._stack):
            self.text.append(d)

    @property
    def visible(self) -> str:
        return " ".join(" ".join(self.text).split())


@pytest.fixture(scope="module")
def pages() -> dict[str, tuple[dict | None, Doc]]:
    out = {"/": (None, Doc(site.render()))}
    for p in landing_pages.PAGES:
        out[p["path"]] = (p, Doc(site.render_landing(p)))
    return out


def test_titles_descriptions_are_unique_and_concise(pages):
    titles = [d.title for _, d in pages.values()]
    descs = [d.description for _, d in pages.values()]
    assert len(set(titles)) == len(titles) and len(set(descs)) == len(descs)
    for path, (_, d) in pages.items():
        assert 30 <= len(d.title) <= 70, (path, d.title)
        assert 90 <= len(d.description) <= 170, (path, len(d.description))
        assert d.title.endswith(" | " + data.BRAND["short"])          # brand as a short suffix


def test_one_h1_and_canonical_per_page(pages):
    for path, (_, d) in pages.items():
        assert len(d.h1s) == 1, (path, d.h1s)
        assert d.canonical == seo.SITE + path


def test_primary_phrase_in_title_h1_description_without_stuffing(pages):
    for path, (p, d) in pages.items():
        phrase = p["primary"] if p else "chauffeur service"
        for where in (d.title, d.h1s[0], d.description):
            assert phrase in where.lower(), (path, where)
        text = d.visible.lower()
        density = text.count(phrase) * len(phrase.split()) / len(text.split())
        assert density <= 0.03, (path, phrase, density)              # reads naturally, never a keyword list


def test_structured_data_is_valid_and_truthful(pages):
    for path, (p, d) in pages.items():
        assert len(d.ld) == 1
        graph = {n["@type"]: n for n in d.ld[0]["@graph"]}
        business = graph["LocalBusiness"]
        assert business["address"] == {"@type": "PostalAddress", "addressRegion": "NJ", "addressCountry": "US"}
        assert "aggregateRating" not in business and "review" not in business
        if p is None:
            assert graph["WebSite"]["name"] == data.BRAND["name"]
            continue
        crumbs = graph["BreadcrumbList"]["itemListElement"]
        assert [c["position"] for c in crumbs] == list(range(1, len(crumbs) + 1))
        assert crumbs[0]["item"] == seo.SITE + "/" and crumbs[-1]["item"] == d.canonical
        faq = graph["FAQPage"]["mainEntity"]
        assert [q["name"] for q in faq] == [seo.fill(q) for q, _ in p["faqs"]]
        if not data.PRICING["approved"]:
            assert "offers" not in graph["Service"]                 # no machine-readable prices until approved


def test_every_advertised_journey_can_be_sold_online():
    """A landing page never promises a route the authority rules turn into a request."""
    cat = get_catalog()
    pairs = list(data.POPULAR_JOURNEYS)
    for p in landing_pages.PAGES:
        pairs += p["routes"] + [sample for *_, sample in p.get("airports", [])]
        copy = json.dumps([p["lede"], p["points"], p["sections"], p["steps"], p["faqs"]])
        pairs += re.findall(r"\{([a-z-]+)>([a-z-]+)\}", copy)
    for a, b in pairs:
        assert pricing.route_class(cat, a, b) in ALLOWED, (a, b)


def test_copy_has_no_unfilled_tokens_or_banned_words(pages):
    for path, (_, d) in pages.items():
        text = d.visible
        assert not re.search(r"\{[a-z_>-]+\}", text), path
        for w in BANNED:
            assert not re.search(rf"\b{re.escape(w)}\b", text, re.I), (path, w)


def test_every_page_is_linked_and_every_link_resolves(pages):
    linked_from_elsewhere = set()
    for path, (_, d) in pages.items():
        for href in d.hrefs:
            if href.startswith("/") and not href.startswith(("/static/", "/api/")):
                target = href.split("#")[0] or "/"
                assert target in KNOWN, (path, href)
                if target != path:
                    linked_from_elsewhere.add(target)
    assert set(landing_pages.BY_PATH) <= linked_from_elsewhere
    assert "/airport-transfers" in pages["/"][1].hrefs                 # home links into the hierarchy


def test_sitemap_dates_follow_content_not_build_day(tmp_path, monkeypatch):
    monkeypatch.setattr(seo, "LASTMOD_FILE", tmp_path / "lastmod.json")
    first = seo.update_lastmod({"/": "<main>a</main>", "/x": "<main>b</main>"}, today="2026-11-01")
    again = seo.update_lastmod({"/": "<main>a</main>?v=20261121", "/x": "<main>b2</main>"}, today="2026-11-21")
    assert first == {"/": "2026-11-01", "/x": "2026-11-01"}
    assert again == {"/": "2026-11-01", "/x": "2026-11-21"}            # only the changed page moves
    xml = seo.sitemap_xml(again)
    assert "changefreq" not in xml and "priority" not in xml           # ignored by Google


def test_landing_pages_are_served_and_staging_is_noindex(client):
    for path in ["/", *landing_pages.BY_PATH]:
        r = client.get(path)
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/html"), path
        assert f'<link rel="canonical" href="{seo.SITE}{path}">' in r.text
        assert r.headers["x-robots-tag"] == "noindex, nofollow"         # APP_ENV=test is not production
    assert client.head("/airport-transfers/newark").status_code == 200
    assert client.get("/sitemap.xml").text.count("<url>") == len(KNOWN)
