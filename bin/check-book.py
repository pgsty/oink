#!/usr/bin/env python3
"""Validate the Book component contract and output matrix."""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from html import unescape
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit

from test_site import run_hugo_process


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/site"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def write(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def build(
    hugo: str,
    source: Path,
    destination: Path,
    *extra: str,
) -> subprocess.CompletedProcess[str]:
    return run_hugo_process(
        [
            hugo,
            "--source",
            str(source),
            "--destination",
            str(destination),
            "--themesDir",
            str(ROOT.parent),
            "--logLevel",
            "warn",
            *extra,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def page_url(public: Path, path: Path) -> str:
    relative = path.relative_to(public).as_posix()
    if relative == "index.html":
        return "/"
    return f"/{relative.removesuffix('index.html')}"


class BookHTML(HTMLParser):
    """Collect the machine-readable Book contract from rendered HTML."""

    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.targets: dict[str, dict[str, object]] = {}
        self.xrefs: list[dict[str, str]] = []
        self.sidebar_links: list[str] = []
        self.pager: dict[str, str] = {}
        self.book_pages: list[str] = []
        self.has_sidebar_headings = False
        self.body_classes: set[str] = set()
        self._figure: dict[str, object] | None = None
        self._figure_caption = False
        self._xref: dict[str, str] | None = None
        self._sidebar_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "body":
            self.body_classes = classes
        if element_id := values.get("id"):
            self.ids.append(element_id)
        if "data-td-book-headings" in values:
            self.has_sidebar_headings = True
        if tag == "nav" and values.get("id") == "td-section-nav":
            self._sidebar_depth = 1
        elif self._sidebar_depth and tag == "nav":
            self._sidebar_depth += 1
        if self._sidebar_depth and tag == "a" and "td-shell-tree__link" in classes:
            if href := values.get("href"):
                self.sidebar_links.append(href)
        if tag == "a":
            for direction in ("prev", "next"):
                if f"data-td-pager-{direction}" in values and values.get("href"):
                    self.pager[direction] = values["href"] or ""
            if "td-book-xref" in classes:
                self._xref = {
                    "href": values.get("href") or "",
                    "kind": values.get("data-td-book-kind") or "",
                    "num": values.get("data-td-book-num") or "",
                    "text": "",
                }
        if tag == "section" and values.get("data-td-book-page"):
            self.book_pages.append(values["data-td-book-page"] or "")
        if tag == "figure" and values.get("data-td-book-kind"):
            target = {
                "id": values.get("id") or "",
                "kind": values.get("data-td-book-kind") or "",
                "num": values.get("data-td-book-num") or "",
                "caption": "",
                "images": [],
            }
            self._figure = target
            if target["id"]:
                self.targets[str(target["id"])] = target
        elif tag == "figcaption" and self._figure is not None:
            self._figure_caption = True
        elif tag == "img" and self._figure is not None:
            images = self._figure["images"]
            assert isinstance(images, list)
            images.append(values)

    def handle_data(self, data: str) -> None:
        if self._xref is not None:
            self._xref["text"] += data
        if self._figure is not None and self._figure_caption:
            self._figure["caption"] = str(self._figure["caption"]) + data

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._xref is not None:
            self._xref["text"] = " ".join(self._xref["text"].split())
            self.xrefs.append(self._xref)
            self._xref = None
        if tag == "figcaption":
            self._figure_caption = False
        elif tag == "figure":
            if self._figure is not None:
                self._figure["caption"] = " ".join(str(self._figure["caption"]).split())
            self._figure = None
        if tag == "nav" and self._sidebar_depth:
            self._sidebar_depth -= 1


def parse_html(source: str) -> BookHTML:
    parser = BookHTML()
    parser.feed(source)
    return parser


def load_book_documents(public: Path) -> dict[str, BookHTML]:
    documents: dict[str, BookHTML] = {}
    book = public / "book"
    if not book.exists():
        return documents
    for path in sorted(book.rglob("index.html")):
        documents[page_url(public, path)] = parse_html(path.read_text(encoding="utf-8"))
    return documents


def load_site_documents(public: Path) -> dict[str, BookHTML]:
    """Load every routed HTML document for consumer-site xref validation."""

    documents: dict[str, BookHTML] = {}
    for path in sorted(public.rglob("index.html")):
        documents[page_url(public, path)] = parse_html(path.read_text(encoding="utf-8"))
    return documents


def validate_documents(
    documents: dict[str, BookHTML],
    *,
    aggregate_unique: bool = True,
) -> list[str]:
    """Validate IDs, image alternatives, and every rendered xref."""

    errors: list[str] = []
    target_owners: dict[str, list[str]] = defaultdict(list)
    referenced_anchors: set[str] = set()
    for url, document in documents.items():
        duplicate_ids = sorted(key for key, count in Counter(document.ids).items() if count > 1)
        for element_id in duplicate_ids:
            errors.append(f"{url} contains duplicate id {element_id!r}")
        for target_id, target in document.targets.items():
            target_owners[target_id].append(url)
            num = str(target["num"])
            kind = str(target["kind"])
            caption = str(target["caption"])
            require(bool(num), f"{url} target {target_id!r} has no number", errors)
            require(
                kind in {"fig", "tbl", "eq", "eg"},
                f"{url} target {target_id!r} has invalid kind {kind!r}",
                errors,
            )
            require(
                num in caption,
                f"{url} target {target_id!r} caption lost number {num!r}",
                errors,
            )
            for image in target["images"]:
                assert isinstance(image, dict)
                require("alt" in image, f"{url} figure {target_id!r} has an image without alt", errors)
                require(
                    bool((image.get("alt") or "").strip()),
                    f"{url} figure {target_id!r} has an empty alt beside a numbered caption",
                    errors,
                )

    for url, document in documents.items():
        for xref in document.xrefs:
            href = xref["href"]
            resolved = urlsplit(urljoin(f"https://example.invalid{url}", href))
            target_url = resolved.path
            if not target_url.endswith("/"):
                target_url += "/"
            anchor = resolved.fragment
            require(bool(anchor), f"{url} xref {href!r} has no anchor", errors)
            if not anchor:
                continue
            referenced_anchors.add(anchor)
            target_document = documents.get(target_url)
            require(target_document is not None, f"{url} xref points to missing page {target_url!r}", errors)
            if target_document is None:
                continue
            require(
                anchor in target_document.ids,
                f"{url} xref points to missing anchor {target_url}#{anchor}",
                errors,
            )
            if not xref["kind"]:
                continue
            target = target_document.targets.get(anchor)
            require(
                target is not None,
                f"{url} {xref['kind']} xref points to non-component anchor {target_url}#{anchor}",
                errors,
            )
            if target is not None:
                require(
                    target["kind"] == xref["kind"],
                    f"{url} xref kind {xref['kind']!r} does not match target kind {target['kind']!r}",
                    errors,
                )
                require(
                    target["num"] == xref["num"],
                    f"{url} xref number {xref['num']!r} does not match target number {target['num']!r}",
                    errors,
                )

    if aggregate_unique:
        aggregate_ids = set(target_owners) | referenced_anchors
        for element_id in sorted(aggregate_ids):
            owners = target_owners.get(element_id, [])
            if len(owners) > 1:
                errors.append(
                    f"aggregate Book output would contain duplicate target id {element_id!r}: "
                    + ", ".join(owners)
                )
    return errors


def check_consumer_public(public: Path) -> list[str]:
    errors: list[str] = []
    require(public.is_dir(), f"consumer public directory does not exist: {public}", errors)
    if not public.is_dir():
        return errors
    documents = load_site_documents(public)
    require(bool(documents), f"consumer public directory contains no routed HTML: {public}", errors)
    target_count = sum(len(document.targets) for document in documents.values())
    xref_count = sum(len(document.xrefs) for document in documents.values())
    require(target_count > 0, "consumer output contains no numbered Book targets", errors)
    require(xref_count > 0, "consumer output contains no Book xrefs", errors)
    errors.extend(validate_documents(documents, aggregate_unique=False))
    return errors


def check_manifest(public: Path) -> list[str]:
    errors: list[str] = []
    path = public / "book/book.json"
    manifests = sorted(public.rglob("book.json"))
    require(manifests == [path], f"BookManifest must be opt-in on exactly the Book root: {manifests}", errors)
    require(path.is_file(), "Book manifest output is missing", errors)
    if not path.is_file():
        return errors
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"Book manifest is invalid JSON: {error}"]

    require(manifest.get("schemaVersion") == 1, "Book manifest schemaVersion is not 1", errors)
    require(manifest.get("language") == "en", "Book manifest language changed", errors)
    pages = manifest.get("pages")
    require(isinstance(pages, list), "Book manifest pages must be a list", errors)
    if not isinstance(pages, list):
        return errors
    expected_paths = [
        "/book",
        "/book/chapter-one",
        "/book/chapter-two",
        "/book/chapter-three",
        "/book/chapter-four",
    ]
    require([page.get("path") for page in pages] == expected_paths, "Book manifest page order changed", errors)
    by_path = {page.get("path"): page for page in pages if isinstance(page, dict)}
    for page in pages:
        require(isinstance(page, dict), "Book manifest contains a non-object page", errors)
        if not isinstance(page, dict):
            continue
        require(isinstance(page.get("number"), str), f"{page.get('path')}: Book number is not a string", errors)
        markdown = page.get("markdown")
        require(isinstance(markdown, str) and bool(markdown), f"{page.get('path')}: Markdown URL is missing", errors)
        if isinstance(markdown, str) and markdown:
            require((public / markdown.lstrip("/")).is_file(), f"{page.get('path')}: Markdown target is missing: {markdown}", errors)
        targets = page.get("targets", [])
        require(isinstance(page.get("aggregateId"), str) and page.get("aggregateId", "").startswith("pg-"),
                f"{page.get('path')}: aggregateId is missing", errors)
        target_ids = {target.get("id") for target in targets if isinstance(target, dict)}
        require(len(target_ids) == len(targets), f"{page.get('path')}: duplicate or invalid target in manifest", errors)

    for page in pages:
        if not isinstance(page, dict):
            continue
        for xref in page.get("xrefs", []):
            if not isinstance(xref, dict):
                errors.append(f"{page.get('path')}: manifest contains a non-object xref")
                continue
            target_page = by_path.get(xref.get("targetPath"))
            require(target_page is not None, f"{page.get('path')}: xref target page is missing: {xref}", errors)
            if not target_page:
                continue
            target_by_id = {
                target.get("id"): target
                for target in target_page.get("targets", [])
                if isinstance(target, dict)
            }
            anchor = xref.get("anchor")
            headings = set(target_page.get("headings", []))
            require(anchor in target_by_id or anchor in headings,
                    f"{page.get('path')}: xref target is missing: {xref}", errors)
            if anchor in target_by_id and xref.get("kind"):
                target = target_by_id[anchor]
                require(target.get("kind") == xref.get("kind") and target.get("num") == xref.get("num"),
                        f"{page.get('path')}: xref kind/number disagrees with target: {xref}", errors)
    require("/Users/" not in path.read_text(encoding="utf-8"), "Book manifest leaked a machine path", errors)
    return errors


def check_home_manifest(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-book-home-manifest-") as temp:
        source = Path(temp)
        write(
            source / "hugo.yaml",
            f"""baseURL: https://example.org/
title: Home Book
theme: {ROOT.name}
disableKinds: [RSS, sitemap, taxonomy, term]
outputs:
  home: [HTML, print, markdown, BookManifest]
  page: [HTML, markdown]
params:
  offline_search: false
  ui:
    pager_types: [book]
""",
        )
        write(
            source / "content/_index.md",
            "---\ntitle: Home Book\ntype: book\nno_print: true\ncascade:\n  type: book\n---\n\nHome.\n",
        )
        write(
            source / "content/chapter.md",
            "---\ntitle: Chapter\n---\n\n"
            '{{< fig num="1-1" id="fig-home" src="/figure.svg" caption="Home figure" />}}\n\n'
            '{{< xref fig="1-1" />}}\n',
        )
        write(source / "static/figure.svg", '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>\n')
        public = source / "public"
        result = build(hugo, source, public, "--printPathWarnings")
        if result.returncode != 0:
            return [f"home BookManifest fixture failed: {result.stdout}{result.stderr}"]
        path = public / "book.json"
        require(path.is_file(), "home BookManifest did not publish /book.json", errors)
        if path.is_file():
            manifest = json.loads(path.read_text(encoding="utf-8"))
            require([page.get("path") for page in manifest.get("pages", [])] == ["/", "/chapter"],
                    "home BookManifest page order or legacy root no_print behavior changed", errors)
            require(manifest.get("book", {}).get("html") == "/", "home BookManifest HTML URL is not the home page", errors)
            require(manifest.get("book", {}).get("print") == "/_print/", "home BookManifest Print URL changed", errors)
            chapter = manifest.get("pages", [{}, {}])[-1]
            require(chapter.get("markdown") == "/chapter/index.md", "home BookManifest chapter Markdown URL changed", errors)
            require([target.get("id") for target in chapter.get("targets", [])] == ["fig-home"],
                    "home BookManifest lost its numbered target", errors)
    return errors


def check_example(public: Path) -> list[str]:
    errors: list[str] = []
    paths = {
        "root": public / "book/index.html",
        "one": public / "book/chapter-one/index.html",
        "two": public / "book/chapter-two/index.html",
        "three": public / "book/chapter-three/index.html",
        "four": public / "book/chapter-four/index.html",
        "root_md": public / "book/index.md",
        "one_md": public / "book/chapter-one/index.md",
        "one_print": public / "_print/book/chapter-one/index.html",
        "book_print": public / "_print/book/index.html",
    }
    for path in paths.values():
        require(path.exists(), f"Book fixture output is missing: {path}", errors)
    if not all(path.exists() for path in paths.values()):
        return errors

    source = {name: path.read_text(encoding="utf-8") for name, path in paths.items()}
    documents = load_book_documents(public)
    errors.extend(validate_documents(documents))
    errors.extend(check_manifest(public))
    expected_pages = {
        "/book/",
        "/book/chapter-one/",
        "/book/chapter-two/",
        "/book/chapter-three/",
        "/book/chapter-four/",
    }
    require(set(documents) == expected_pages, "Book example must contain exactly four chapters", errors)

    one = documents.get("/book/chapter-one/")
    two = documents.get("/book/chapter-two/")
    three = documents.get("/book/chapter-three/")
    four = documents.get("/book/chapter-four/")
    root = documents.get("/book/")
    if one and two and three and four and root:
        require("td-book-content--normal" in one.body_classes, "Book default reading width is not normal", errors)
        require(
            one.sidebar_links[:5]
            == [
                "/book/",
                "/book/chapter-one/",
                "/book/chapter-two/",
                "/book/chapter-three/",
                "/book/chapter-four/",
            ],
            "Book sidebar order changed",
            errors,
        )
        require(one.pager == {"prev": "/book/", "next": "/book/chapter-two/"}, "Book pager does not follow sidebar pre-order", errors)
        require(two.pager == {"prev": "/book/chapter-one/", "next": "/book/chapter-three/"}, "middle Book page pager is wrong", errors)
        require(three.pager == {"prev": "/book/chapter-two/", "next": "/book/chapter-four/"}, "middle Book page pager is wrong", errors)
        require(four.pager == {"prev": "/book/chapter-three/"}, "last Book page pager is wrong", errors)
        require(two.has_sidebar_headings, "active Book page has no sidebar heading branch", errors)
        # Every chapter carries two or more of each numbered kind so the
        # fixture exercises shortcode and native authoring side by side.
        target_sets = {
            "one": (one, {
                "fig-overview", "fig-artifact",
                "tbl-baseline", "tbl-outputs",
                "eq-coverage", "eq-weighted",
                "eg-baseline", "eg-inventory",
            }),
            "two": (two, {
                "fig-release",
                "tbl-release", "tbl-states",
                "eq-readiness", "eq-propagation",
                "eg-manifest", "eg-checksums", "eg-tag",
            }),
            "three": (three, {
                "fig-operations",
                "tbl-operations", "tbl-failure-model",
                "eq-budget", "eq-detect", "eq-rto",
                "eg-review", "eg-profile",
            }),
            "four": (four, {
                "tbl-notation", "tbl-backprop",
                "eq-layer", "eq-sigmoid", "eq-bp1",
                "eg-network", "eg-training",
            }),
        }
        for name, (document, expected) in target_sets.items():
            require(set(document.targets) == expected, f"chapter {name} target registry changed: {sorted(document.targets)}", errors)

        for document, target_id, image_src in (
            (one, "fig-overview", "/images/oink.webp"),
            (two, "fig-release", "/images/releasenote.webp"),
            (three, "fig-operations", "/images/oink.webp"),
        ):
            figure = document.targets.get(target_id)
            if not figure:
                continue
            images = figure["images"]
            require(len(images) == 1, f"{target_id} image is missing", errors)
            if images:
                image = images[0]
                require(image.get("src") == image_src, f"{target_id} src changed", errors)
                require(
                    image.get("width") == "600" and image.get("height") == "300",
                    f"{target_id} dimensions were lost",
                    errors,
                )

    toc = re.search(r'<nav class="td-book-toc[\s\S]*?</nav>', source["root"])
    require(toc is not None, "Book table of contents is missing", errors)
    if toc:
        toc_source = toc.group(0)
        for marker in (
            "/book/chapter-one/",
            "/book/chapter-two/",
            "/book/chapter-three/",
            "/book/chapter-four/",
            "#describe-system",
            "#delivery-states",
            "#observe-result",
            "#four-equations",
        ):
            require(marker in toc_source, f"depth-three Book ToC lost {marker}", errors)
        for marker in ("/docs/", "/blog/", "/landing-demo/"):
            require(marker not in toc_source, f"Book ToC escaped its root through {marker}", errors)
        require("<ol class=td-book-toc__headings" in toc_source or '<ol class="td-book-toc__headings' in toc_source, "Book ToC lost heading lists", errors)
        require("<ol class=td-book-toc__headings><ol" not in toc_source, "Book ToC contains an empty wrapper list", errors)

    # Every list runs in document order, and each chapter authors some targets
    # as shortcodes and some in native form: one form sorting ahead of the other
    # would put Figure 1-2 before Figure 1-1.
    expected_lists = {
        "fig": ["Figure 1-1", "Figure 1-2", "Figure 2-1", "Figure 3-1"],
        "tbl": [
            "Table 1-1", "Table 1-2", "Table 2-1", "Table 2-2",
            "Table 3-1", "Table 3-2", "Table 4-1", "Table 4-2",
        ],
        "eq": [
            "Equation 1.1", "Equation 1.2", "Equation 2.1", "Equation 2.2",
            "Equation 3.1", "Equation 3.2", "Equation 3.3",
            "Equation 4.1", "Equation 4.2", "Equation 4.3",
        ],
        "eg": [
            "Example 1-1", "Example 1-2", "Example 2-1", "Example 2-2",
            "Example 2-3", "Example 3-1", "Example 3-2",
            "Example 4-1", "Example 4-2",
        ],
    }
    for kind in ("fig", "tbl", "eq", "eg"):
        require(
            f'td-book-figures--{kind}' in source["root"],
            f"Book index lost the {kind} list",
            errors,
        )
        listing = re.search(
            rf'td-book-figures--{kind}"?>(.*?)</ol>', source["root"], re.DOTALL
        )
        require(listing is not None, f"Book index {kind} list is unreadable", errors)
        if listing:
            labels = re.findall(
                r'td-book-label"?>([^<]+)<', listing.group(1)
            )
            require(
                labels == expected_lists[kind],
                f"Book {kind} list is not in document order: {labels}",
                errors,
            )
    for marker in (
        "Figure 1-1", "Figure 1-2", "Figure 2-1", "Figure 3-1",
        "Table 1-1", "Table 1-2", "Table 2-1", "Table 3-1", "Table 4-1", "Table 4-2",
        "Equation 1.1", "Equation 1.2", "Equation 2.1", "Equation 3.1", "Equation 3.3", "Equation 4.1",
        "Example 1-1", "Example 2-1", "Example 2-3", "Example 3-1", "Example 4-1",
        "/book/chapter-one/#fig-overview",
        "/book/chapter-one/#fig-artifact",
        "/book/chapter-two/#fig-release",
        "/book/chapter-three/#fig-operations",
        "/book/chapter-four/#tbl-backprop",
    ):
        require(marker in source["root"], f"Book figure list lost {marker}", errors)
    for marker in ("td-book-draft-badge", "td-book-draft", "data-td-book-headings", "#delivery-states"):
        require(marker in source["two"], f"draft/sidebar output lost {marker}", errors)
    for name in ("one", "two", "three", "four"):
        for marker in ("td-table-scroll", 'class="katex-display"', "third_party/katex/katex.min.", "td-book-figure--eg"):
            require(marker in source[name], f"chapter {name} lost {marker}", errors)
    require("Query a small evidence table before publishing." not in (toc.group(0) if toc else ""), "example caption leaked into Book ToC", errors)

    for marker in (
        "**Figure 1-1.**",
        "![OINK documentation site overview](/images/oink.webp)",
        "**Table 1-1.**",
        "**Equation 1.1.**",
        "**Example 1-1.**",
        "SELECT surface, verified",
    ):
        require(marker in source["one_md"], f"Markdown Book output lost {marker}", errors)
    for forbidden in ("<figure", "td-book-figure", "katex-html", "td-table-scroll"):
        require(forbidden not in source["one_md"], f"Markdown Book output leaked {forbidden}", errors)
    for marker in (
        "- [1 Establish the baseline]",
        "- [2 Release workflow]",
        "- [3 Operate and review]",
        "- [4 Formulas and derivations]",
        "- [Figure 1-1]", "- [Figure 1-2]", "- [Figure 2-1]", "- [Figure 3-1]",
        "- [Table 1-1]", "- [Table 1-2]", "- [Table 2-1]", "- [Table 3-1]", "- [Table 4-1]",
        "- [Equation 1.1]", "- [Equation 1.2]", "- [Equation 2.1]", "- [Equation 3.1]", "- [Equation 4.1]",
        "- [Example 1-1]", "- [Example 2-1]", "- [Example 3-1]", "- [Example 4-1]",
    ):
        require(marker in source["root_md"], f"Markdown Book index lost {marker}", errors)

    require("td-table-scroll--static" in source["one_print"], "print Book table wrapper is not marked static", errors)
    require(re.search(r'td-table-scroll[^>]*tabindex="0"[^>]*role="region"', source["one_print"]) is not None, "Book Print preview lost its keyboard table scroll region", errors)
    for marker in (
        'id="fig-overview"',
        'id="tbl-baseline"',
        'id="eq-coverage"',
        "Figure 1-1",
        "Table 1-1",
        'class="td-book-figure td-book-figure--eg"',
    ):
        require(marker in source["one_print"], f"chapter print lost {marker}", errors)
    for marker in ('id="describe-system"', 'id="fn:1"', 'href="#fn:1"'):
        require(marker in source["one_print"], f"single-page Print changed page-local anchor {marker}", errors)
    require(
        re.search(r'id="pg-[^"]+--describe-system"', source["one_print"]) is None,
        "single-page Print namespaced an ordinary heading anchor",
        errors,
    )
    require(
        'id="fn:pg-' not in source["one_print"],
        "single-page Print namespaced a page-local footnote anchor",
        errors,
    )
    aggregate = parse_html(source["book_print"])
    require(
        aggregate.book_pages
        == [
            "/book",
            "/book/chapter-one",
            "/book/chapter-two",
            "/book/chapter-three",
            "/book/chapter-four",
        ],
        "whole-Book print order changed",
        errors,
    )
    duplicate_aggregate_ids = sorted(key for key, count in Counter(aggregate.ids).items() if count > 1)
    require(not duplicate_aggregate_ids, f"whole-Book print contains duplicate IDs: {duplicate_aggregate_ids}", errors)
    require(
        "third_party/katex/katex.min." in source["book_print"],
        "whole-Book print did not propagate child mathematics to the KaTeX stylesheet gate",
        errors,
    )
    # Footnotes are numbered per page, so the aggregate must namespace them the
    # way it namespaces heading IDs; chapters one to four all carry references.
    require(
        re.search(r'id="pg-[^"]+--describe-system"', source["book_print"]) is not None,
        "whole-Book print did not namespace heading IDs",
        errors,
    )
    require('id="fn:pg-' in source["book_print"], "whole-Book print did not namespace footnote IDs", errors)
    require('id="fn:1"' not in source["book_print"], "whole-Book print kept a page-local footnote ID", errors)
    for element_id in (
        "fig-overview", "fig-artifact", "tbl-baseline", "tbl-outputs",
        "eq-coverage", "eq-weighted", "eg-baseline", "eg-inventory",
        "fig-release", "tbl-release", "tbl-states", "eq-readiness",
        "eq-propagation", "eg-manifest", "eg-checksums", "eg-tag",
        "fig-operations", "tbl-operations", "tbl-failure-model",
        "eq-budget", "eq-detect", "eq-rto", "eg-review", "eg-profile",
        "tbl-notation", "tbl-backprop", "eq-layer", "eq-sigmoid",
        "eq-bp1", "eg-network", "eg-training",
    ):
        require(source["book_print"].count(f'id={element_id}') + source["book_print"].count(f'id="{element_id}"') == 1, f"whole-Book print does not preserve one {element_id!r}", errors)
    for marker in ('href="#fig-overview"', 'href="#eq-readiness"', 'href="#eg-baseline"'):
        require(marker in source["book_print"], f"whole-Book print did not localize {marker}", errors)
    for marker in ("td-pager", "data-td-pager-prev", "data-td-pager-next"):
        require(marker not in source["book_print"], f"whole-Book print retained interactive marker {marker}", errors)
    # Static content stays keyboard-scrollable in the browser's Print preview.
    require("td-table-scroll--static" in source["book_print"], "whole-Book print table wrapper is not marked static", errors)
    require(re.search(r'td-table-scroll[^>]*tabindex="0"[^>]*role="region"', source["book_print"]) is not None, "whole-Book Print preview lost its keyboard table scroll region", errors)
    return errors


def base_config(extra_ui: str = "") -> str:
    return f"""baseURL: https://example.org/
title: Book fixture
theme: {ROOT.name}
defaultContentLanguage: en
disableKinds: [home, RSS, sitemap, taxonomy, term]
markup:
  goldmark:
    renderer:
      unsafe: true
    parser:
      wrapStandAloneImageWithinParagraph: false
      attribute:
        block: true
outputs:
  page: [HTML]
  section: [HTML]
params:
  ui:
    shell_types: [book]
    sidebar_root_enabled: true
    sidebar_root_menu: false
    pager_types: [book]
{extra_ui}"""


def create_site(root: Path, body: str, *, extra_ui: str = "", draft: bool = False) -> None:
    write(root / "hugo.yaml", base_config(extra_ui))
    write(
        root / "content/book/_index.md",
        "---\ntitle: Book\ntype: book\ncascade:\n  type: book\n---\n",
    )
    status = "book_status: draft\n" if draft else ""
    write(root / "content/book/page.md", f"---\ntitle: Page\n{status}---\n\n{body}\n")


def check_invalid_number_outputs(hugo: str) -> list[str]:
    """Invalid numbers preserve bodies without inventing targets or index rows."""
    errors: list[str] = []
    cases = {
        "figure": ('{{< fig num="1/2" id="discarded" src="/x.png" caption="Figure fallback" />}}', "Figure fallback"),
        "table": ('{{< tbl num="1/2" id="discarded" caption="Table fallback" >}}\n| Value |\n| --- |\n| Kept table |\n{{< /tbl >}}', "Kept table"),
        "equation": ('{{< eq num="1/2" id="discarded" caption="Equation fallback" >}}x+y{{< /eq >}}', "Equation fallback"),
        "example": ('{{< eg num="1/2" id="discarded" caption="Example fallback" >}}Example body{{< /eg >}}', "Example body"),
        "native-table": ('| Value |\n| --- |\n| Native table |\n{num="1/2" caption="Table fallback"}', "Native table"),
        "native-code": ('```text {num="1/2" caption="Example fallback"}\nNative code\n```', "Native code"),
        "figure-positional": ('{{< fig "bad" >}}Figure body{{< /fig >}}', "Figure body"),
        "table-positional": ('{{< tbl "bad" >}}\n| Value |\n| --- |\n| Table body |\n{{< /tbl >}}', "Table body"),
        "example-positional": ('{{< eg "bad" >}}Example body{{< /eg >}}', "Example body"),
    }
    with tempfile.TemporaryDirectory(prefix="oink-book-number-fallbacks-") as temp:
        site = Path(temp)
        write(site / "hugo.yaml", base_config().replace(
            "page: [HTML]", "page: [HTML, PRINT, MARKDOWN]"
        ).replace("section: [HTML]", "section: [HTML, PRINT, MARKDOWN, BookManifest]"))
        write(site / "content/book/_index.md",
              "---\ntitle: Book\ntype: book\ncascade:\n  type: book\n---\n\n"
              "{{< book-figures >}}\n{{< book-tables >}}\n"
              "{{< book-equations >}}\n{{< book-examples >}}\n")
        for name, (body, _) in cases.items():
            write(site / f"content/book/{name}.md", f"---\ntitle: {name}\n---\n\n{body}\n")
        write(site / "content/book/valid.md", """---
title: Valid numbers
---
{{< fig num="9" src="/x.png" caption="Valid figure" />}}
{{< tbl num="9" caption="Valid table" >}}
| Value |
| --- |
| Valid table |
{{< /tbl >}}
{{< eq num="9" >}}x+y{{< /eq >}}
{{< eg num="9" caption="Valid example" >}}Valid body{{< /eg >}}
""")
        public = site / "public"
        result = build(hugo, site, public)
        log = result.stdout + result.stderr
        require(result.returncode == 0, f"invalid-number matrix stopped the build: {log}", errors)
        if result.returncode != 0:
            return errors
        for name, (_, body_marker) in cases.items():
            require(f"content/book/{name}.md:" in log, f"{name}: invalid number/argument emitted no diagnostic", errors)
            for relative in (f"book/{name}/index.html", f"_print/book/{name}/index.html", f"book/{name}/index.md"):
                rendered = (public / relative).read_text()
                require(body_marker in rendered, f"{relative}: unnumbered fallback lost its body", errors)
                require('id="discarded"' not in rendered and 'data-td-book-num=' not in rendered
                        and re.search(r'id="(?:fig|tbl|eq|eg)-"', rendered) is None,
                        f"{relative}: invalid number emitted a Book target", errors)
        manifest = json.loads((public / "book/book.json").read_text())
        pages = {page["path"]: page for page in manifest["pages"]}
        for name in cases:
            require(f"/book/{name}" in pages and pages[f"/book/{name}"]["targets"] == [],
                    f"{name}: invalid number was registered in BookManifest", errors)
        valid_ids = {f"{kind}-9" for kind in ("fig", "tbl", "eq", "eg")}
        require({target["id"] for target in pages.get("/book/valid", {}).get("targets", [])} == valid_ids,
                "invalid-number protection dropped valid Book targets", errors)
        for relative in ("book/index.html", "book/index.md"):
            index = (public / relative).read_text()
            for target in valid_ids:
                require(f"/book/valid/#{target}" in index, f"{relative}: valid index entry {target} disappeared", errors)
            require("discarded" not in index and not any(f"/book/{name}/#" in index for name in cases),
                    f"{relative}: invalid number appeared in a Book index", errors)
    return errors


def check_sidebar_headings(hugo: str) -> list[str]:
    """Headings are opt-in, page overrides win, and cached trees stay neutral."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-book-sidebar-") as temp:
        source = Path(temp)
        create_site(source, "")
        pages = {
            "default": ("", None),
            "off": ("sidebar_headings: false\n", 0),
            "two": ("sidebar_headings: true\n", 2),
            "three": ("sidebar_headings: 3\n", 3),
            "four": ("sidebar_headings: 4\n", 4),
            "part/inherited": ("", 3),
            "part/off": ("sidebar_headings: false\n", 0),
        }
        write(source / "content/book/part/_index.md",
              "---\ntitle: Part\ncascade:\n  sidebar_headings: 3\n---\n")
        for name, (settings, _) in pages.items():
            write(source / f"content/book/{name}.md",
                  f"---\ntitle: {name}\n{settings}---\n\n"
                  "## Heading two {#h2}\n\nText.\n\n"
                  "### Heading three {#h3}\n\nText.\n\n"
                  "#### Heading four {#h4}\n\nText.\n")
        # Exercise both navigation authorities and both sides of the cache
        # threshold. Enabled pages must not leak headings into cached siblings.
        for explicit in (False, True):
            if explicit:
                write(source / "data/docs_nav.json", json.dumps({"sections": [{
                    "page": "/book", "children": [
                        {"page": f"/book/{name}"} for name in pages
                    ],
                }]}))
            for site_depth in (None, 4):
                ui = "    sidebar_cache_limit: 1\n" if site_depth is None else "    sidebar_cache_limit: 500\n    sidebar_headings: 4\n"
                write(source / "hugo.yaml", base_config(ui))
                public = source / "public"
                result = build(hugo, source, public)
                if result.returncode:
                    return [f"Book sidebar fixture failed: {result.stdout}{result.stderr}"]
                for name, (_, depth) in pages.items():
                    html = (public / f"book/{name}/index.html").read_text()
                    branch = re.findall(r'<div[^>]*data-td-book-headings[^>]*>(.*?)</div>', html, re.S)
                    expected = (site_depth or 0) if depth is None else depth
                    label = f"{name} (explicit={explicit}, site={site_depth})"
                    require(len(branch) == int(expected > 0), f"wrong Book heading branch count: {label}", errors)
                    if branch:
                        require(re.findall(r'href="#(h[234])"', branch[0]) ==
                                [f"h{level}" for level in range(2, expected + 1)],
                                f"wrong Book heading depth: {label}", errors)
                    require('id="TableOfContents"' in html,
                            f"Book sidebar setting removed the right TOC: {label}", errors)
    return errors


def check_toc_heading_entities(hugo: str) -> list[str]:
    """Fragment titles are already entity-encoded; Book HTML must decode them
    once before the template context performs its final escaping."""

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-book-toc-entities-") as temp:
        source = Path(temp)
        write(source / "hugo.yaml", base_config())
        write(
            source / "content/book/_index.md",
            """---
title: Book
type: book
outputs: [HTML, print]
cascade:
  type: book
---

{{< book-toc depth=3 >}}
""",
        )
        write(
            source / "content/book/page.md",
            """---
title: Page
book_kind: chapter
book_number: 1
---

## Reader's question {#reader-question}
""",
        )
        result = build(hugo, source, source / "public")
        if result.returncode != 0:
            return [f"Book heading-entity fixture failed: {result.stdout}{result.stderr}"]

        paths = {
            "Book ToC": source / "public/book/index.html",
            "whole-Book print ToC": source / "public/_print/book/index.html",
        }
        for label, path in paths.items():
            require(path.exists(), f"{label} output is missing", errors)
            if not path.exists():
                continue
            toc = re.search(
                r'<nav class="td-book-toc[\s\S]*?</nav>',
                path.read_text(encoding="utf-8"),
            )
            require(toc is not None, f"{label} is missing", errors)
            if toc is None:
                continue
            rendered = unescape(toc.group(0))
            require(
                "Reader’s question" in rendered,
                f"{label} double-escaped the heading apostrophe",
                errors,
            )
            require(
                "Reader&rsquo;s question" not in rendered,
                f"{label} exposed an HTML entity as text",
                errors,
            )
    return errors


def check_toc_drafts(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-book-toc-drafts-") as temp:
        source = Path(temp)
        write(source / "hugo.yaml", base_config())
        cases = (
            ("true", "true", True),
            ("false", "false", False),
            ("invalid", '""', True),
        )
        for name, value, _ in cases:
            write(
                source / f"content/{name}/_index.md",
                f"---\ntitle: {name}\ntype: book\ncascade:\n  type: book\n---\n\n{{{{< book-toc drafts={value} >}}}}\n",
            )
            write(
                source / f"content/{name}/draft.md",
                f"---\ntitle: Draft {name}\nbook_status: draft\n---\n",
            )

        result = build(hugo, source, source / "public")
        output = result.stdout + result.stderr
        require(result.returncode == 0, "invalid book-toc drafts stopped the ordinary build", errors)
        require("drafts must be boolean" in output, "invalid book-toc drafts emitted no warning", errors)
        if result.returncode == 0:
            for name, _, includes_draft in cases:
                page = source / f"public/{name}/index.html"
                toc = re.search(r'<nav class="td-book-toc[\s\S]*?</nav>', page.read_text(encoding="utf-8"))
                require(toc is not None, f"book-toc drafts={name} output is missing", errors)
                if toc is not None:
                    present = f"Draft {name}" in toc.group(0)
                    require(
                        present == includes_draft,
                        f"book-toc drafts={name} used the wrong draft visibility",
                        errors,
                    )

    return errors


def check_print_store_isolation(hugo: str) -> list[str]:
    """Plain and aggregate Print may render one Book page concurrently."""

    errors: list[str] = []

    def check_aggregate_tabs(html: str, sections: range, label: str) -> None:
        ids = re.findall(r'\sid="([^"]+)"', html)
        require(len(ids) == len(set(ids)), f"{label} contains duplicate IDs", errors)
        for section in sections:
            for page in range(3):
                chapter = re.search(
                    rf'<section[^>]*id="(pg-[^"]+)"[^>]*data-td-book-page="/book/s{section}/p{page}"[^>]*>([\s\S]*?)</section>',
                    html,
                )
                require(chapter is not None, f"{label} lost chapter {section}-{page}", errors)
                if chapter is None:
                    continue
                prefix, content = chapter.groups()
                anchor = f"probe-{section}-{page}-one"
                require(f'id="{prefix}--{anchor}"' in content
                        and f'href="#{prefix}--{anchor}"' in content
                        and f'id="{anchor}"' not in content
                        and f'--probe-{section}-{page}-2-one"' not in content,
                        f"{label} tab link does not target its own chapter {section}-{page}", errors)

    with tempfile.TemporaryDirectory(prefix="oink-book-print-store-") as temp:
        source = Path(temp)
        write(
            source / "hugo.yaml",
            f"""baseURL: https://example.org/
title: Book Print store fixture
theme: {ROOT.name}
defaultContentLanguage: en
disableKinds: [home, RSS, sitemap, taxonomy, term]
markup:
  goldmark:
    renderer:
      unsafe: true
outputs:
  page: [HTML, print]
  section: [HTML, print]
params:
  offline_search: false
  ui:
    shell_types: [book]
    sidebar_root_enabled: true
    sidebar_root_menu: false
""",
        )
        write(
            source / "layouts/_shortcodes/aggregate-probe.html",
            """{{- $before := .Page.Store.Get "tdBookAggregate" | default false -}}
{{- $sink := 0 -}}
{{- range seq 1 2000 -}}{{- $sink = add $sink . -}}{{- end -}}
<span data-aggregate-probe="{{ $before }}-{{ .Page.Store.Get "tdBookAggregate" | default false }}-{{ $sink }}"></span>
""",
        )
        write(
            source / "content/book/_index.md",
            "---\ntitle: Book\ntype: book\ncascade:\n  type: book\n  outputs: [HTML, print]\n---\n",
        )
        calls = "\n".join("{{< aggregate-probe >}}" for _ in range(6))
        for section in range(2):
            write(
                source / f"content/book/s{section}/_index.md",
                f"---\ntitle: Section {section}\nweight: {section}\n---\n",
            )
            for page in range(3):
                target = (page + 1) % 3
                write(
                    source / f"content/book/s{section}/p{page}.md",
                    f"---\ntitle: Page {section}-{page}\nweight: {page}\n---\n\n"
                    "## Topic {#topic}\n\n"
                    "{{< xref anchor=\"topic\" >}}Self{{< /xref >}}\n\n"
                    f"{{{{< xref page=\"/book/s{section}/p{target}\" anchor=\"topic\" >}}}}Cross{{{{< /xref >}}}}\n\n"
                    f'<a href="#probe-{section}-{page}-one">Self tab</a>\n\n'
                    f"{{{{< tabs group=\"probe-{section}-{page}\" >}}}}\n"
                    "{{< tab label=\"One\" value=\"one\" >}}One{{< /tab >}}\n"
                    "{{< tab label=\"Two\" value=\"two\" >}}Two{{< /tab >}}\n"
                    "{{< /tabs >}}\n\n"
                    f"{calls}\n",
                )

        baseline: tuple[str, ...] | None = None
        for run in range(2):
            public = source / f"public-{run}"
            result = build(hugo, source, public)
            if result.returncode != 0:
                return [f"Book Print store fixture failed on run {run + 1}: {result.stdout}{result.stderr}"]

            rendered: list[str] = []
            for section in range(2):
                for page in range(3):
                    plain = (public / f"_print/book/s{section}/p{page}/index.html").read_text()
                    rendered.append(plain)
                    require(plain.count('data-aggregate-probe="false-false-') == 6,
                            f"plain Print observed aggregate state on run {run + 1}, page {section}-{page}", errors)
                    require('id="topic"' in plain and 'href="#topic"' in plain
                            and f'href="/book/s{section}/p{(page + 1) % 3}/#topic"' in plain,
                            f"plain Print xref or heading semantics changed on page {section}-{page}", errors)
                    require(f'id="probe-{section}-{page}-one"' in plain
                            and f'href="#probe-{section}-{page}-one"' in plain
                            and f'id="probe-{section}-{page}-2-one"' not in plain,
                            f"plain Print tab anchors changed on page {section}-{page}", errors)

                aggregate = (public / f"_print/book/s{section}/index.html").read_text()
                rendered.append(aggregate)
                require(aggregate.count('data-aggregate-probe="true-true-') == 18,
                        f"nested Book Print lost aggregate state on run {run + 1}, section {section}", errors)
                require('id="topic"' not in aggregate and 'href="/book/' not in aggregate
                        and re.search(r'id="pg-[^"]+--topic"', aggregate) is not None,
                        f"nested Book Print xref or heading semantics changed in section {section}", errors)
                check_aggregate_tabs(aggregate, range(section, section + 1),
                                     f"nested Book Print section {section}")

            whole = (public / "_print/book/index.html").read_text()
            rendered.append(whole)
            require(whole.count('data-aggregate-probe="true-true-') == 36,
                    f"whole-Book Print lost aggregate state on run {run + 1}", errors)
            require('id="topic"' not in whole and 'href="/book/' not in whole
                    and len(re.findall(r'id="pg-[^"]+--topic"', whole)) == 6,
                    "whole-Book Print xref or heading semantics changed", errors)
            check_aggregate_tabs(whole, range(2), "whole-Book Print")
            signature = tuple(rendered)
            require(baseline is None or signature == baseline,
                    f"Book Print stress output changed between repeated builds on run {run + 1}", errors)
            baseline = signature
    return errors


def check_reading_time(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-book-reading-time-") as temp:
        source = Path(temp)
        create_site(source, "Book chapter words.\n", extra_ui="    reading_time: true\n")
        write(source / "content/docs/_index.md", "---\ntitle: Docs\ntype: docs\n---\n")
        write(source / "content/docs/page.md", "---\ntitle: Docs page\ntype: docs\n---\n\nDocs page words.\n")
        result = build(hugo, source, source / "public")
        if result.returncode != 0:
            return [f"Book reading-time fixture failed: {result.stdout}{result.stderr}"]
        book = (source / "public/book/page/index.html").read_text(encoding="utf-8")
        docs = (source / "public/docs/page/index.html").read_text(encoding="utf-8")
        require('class="td-reading-time"' not in book, "Book chapter retained reading-time metadata", errors)
        require('class="td-reading-time"' in docs, "Book reading-time guard suppressed regular docs metadata", errors)
    return errors


def check_invalid_components(hugo: str) -> list[str]:
    errors: list[str] = []
    cases = (
        ("missing-num", '{{< fig src="/x.png" />}}', "requires parameter num"),
        ("num-type", '{{< fig num=1 src="/x.png" />}}', "num must be a string"),
        ("num-grammar", '{{< fig num="1/2" src="/x.png" />}}', "num must match"),
        ("id-grammar", '{{< fig num="1" id="1bad" src="/x.png" />}}', "id must match"),
        ("duplicate-id", '{{< fig num="1" id="same" src="/x.png" />}}\n{{< tbl num="2" id="same" >}}x{{< /tbl >}}', "duplicate id"),
        ("duplicate-num", '{{< fig num="1" id="one" src="/x.png" />}}\n{{< fig num="1" id="two" src="/y.png" />}}', "duplicate fig number"),
        ("unsupported", '{{< fig num="1" src="/x.png" bogus="x" />}}', "unsupported parameter"),
        ("src-inner", '{{< fig num="1" src="/x.png" >}}body{{< /fig >}}', "mutually exclusive"),
        ("fig-caption-title", '{{< fig num="1" src="/x.png" caption="Kept caption" title="Dropped title" />}}', "using caption"),
        ("empty-table", '{{< tbl num="1" >}}{{< /tbl >}}', "requires inner table content"),
        ("bad-width", '{{< fig num="1" src="/x.png" width="0" />}}', "must be a positive integer"),
        ("many-kinds", '{{< xref fig="1" tbl="1" />}}', "accepts only one"),
        ("xref-empty", '{{< xref >}}Kept reference{{< /xref >}}', "requires fig, tbl, eq, eg, or anchor"),
        ("xref-anchor-text", '{{< xref anchor="heading" />}}', "requires inner link text"),
        ("xref-page", '{{< xref page="missing" anchor="heading" >}}Kept reference{{< /xref >}}', "was not found"),
        ("toc-depth", '{{< book-toc depth=4 >}}', "depth must be an integer from 1 through 3"),
        ("eg-caption", '{{< eg num="1" >}}```sql\nSELECT 1;\n```{{< /eg >}}', "requires parameter caption"),
        ("eg-num", '{{< eg num="1/2" caption="Bad" >}}x{{< /eg >}}', "num must match"),
        ("eg-empty", '{{< eg num="1" caption="Empty" >}}{{< /eg >}}', "requires inner content"),
        ("fence-caption-without-num", '```sql {caption="orphan"}\nSELECT 1;\n```', "caption requires num"),
        ("fence-num-without-caption", '```sql {num="1"}\nSELECT 1;\n```', "requires caption"),
        ("table-num-and-tab", '| A |\n| --- |\n| 1 |\n{num="1" tab="x"}', "mutually exclusive"),
        ("table-unknown-attr", '| A |\n| --- |\n| 1 |\n{bogus="1"}', "unknown attribute"),
        ("table-style-attr", '| A |\n| --- |\n| 1 |\n{style="color:red"}', "unsafe attribute"),
        ("book-figures-kind", '{{< book-figures kind="tbl" >}}', "unsupported parameter"),
        # A shortcode body is its own Goldmark document: a page-level footnote
        # definition is unreachable from it, and a body-level one builds a
        # second footnote list whose ids collide with the page's own.
        (
            "footnote-page-definition",
            '{{< tbl num="1" caption="Notes" >}}\n| a |\n| --- |\n| x [^n1] |\n{{< /tbl >}}\n\n[^n1]: Page note.',
            "footnote reference [^n1] cannot be used inside a shortcode body",
        ),
        (
            "footnote-body-definition",
            '{{< eg num="1" caption="Notes" >}}\nBody [^n2]\n\n[^n2]: Body note.\n{{< /eg >}}',
            "footnote reference [^n2] cannot be used inside a shortcode body",
        ),
    )
    for name, body, expected in cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-components-book-invalid-{name}-") as temp:
            source = Path(temp)
            create_site(source, body)
            if name in ("xref-empty", "xref-page", "fig-caption-title"):
                config = source / "hugo.yaml"
                config.write_text(config.read_text().replace("page: [HTML]", "page: [HTML, PRINT, MARKDOWN]"))
            result = build(hugo, source, source / "public")
            output = result.stdout + result.stderr
            require(result.returncode == 0,
                    f"invalid Book case {name} stopped the ordinary build", errors)
            require(expected in output, f"invalid Book case {name} did not report {expected!r}", errors)
            require((source / "public/book/page/index.html").is_file(),
                    f"invalid Book case {name} emitted no safe page output", errors)
            if name in ("missing-num", "num-type", "num-grammar", "eg-num"):
                rendered = (source / "public/book/page/index.html").read_text()
                require('id="fig-"' not in rendered and 'id="tbl-"' not in rendered
                        and 'id="eg-"' not in rendered and 'id="eq-"' not in rendered,
                        f"invalid Book case {name} emitted an empty Book target id", errors)
            if name in ("xref-empty", "xref-page", "fig-caption-title"):
                for relative in ("book/page/index.html", "_print/book/page/index.html", "book/page/index.md"):
                    rendered = (source / "public" / relative).read_text()
                    if name == "fig-caption-title":
                        require("Kept caption" in rendered and "Dropped title" not in rendered,
                                f"{relative} did not prefer fig caption", errors)
                    else:
                        require("Kept reference" in rendered and "td-book-xref" not in rendered
                                and "[Kept reference](" not in rendered,
                                f"{relative} linked a missing xref target", errors)

    config_cases = (
        ("headings", "    sidebar_headings: 1\n", "", False, "params.ui.sidebar_headings"),
        ("banner", '    book_draft_banner: "yes"\n', "", True, "params.ui.book_draft_banner"),
        ("reading-width", "", "  reading_width: broad\n", False, "invalid params.reading_width"),
    )
    for name, extra_ui, extra_params, draft, expected in config_cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-components-book-config-{name}-") as temp:
            source = Path(temp)
            create_site(source, "## Heading\n", extra_ui=extra_ui, draft=draft)
            if extra_params:
                config = source / "hugo.yaml"
                config.write_text(config.read_text(encoding="utf-8").replace("params:\n", "params:\n" + extra_params), encoding="utf-8")
            result = build(hugo, source, source / "public")
            output = result.stdout + result.stderr
            require(expected in output, f"invalid Book config {name} did not report {expected!r}", errors)


            require(result.returncode == 0,
                    f"invalid Book config {name} stopped the build instead of warning", errors)
            require((source / "public/book/page/index.html").is_file(),
                    f"invalid Book config {name} emitted no safe page output", errors)
    return errors


def check_footnotes(hugo: str) -> list[str]:
    """Footnotes belong to the page document: native forms carry them, scoped
    shortcode bodies refuse them, and footnote-shaped code is left alone."""

    errors: list[str] = []
    body = (
        "Prose [^n1] and [^n2].\n\n"
        "| a | b |\n| --- | --- |\n| x [^n1] | y [^n2] |\n"
        '{#tab_notes num="1-1" caption="Numbered table with footnotes"}\n\n'
        '{{< eg num="1-1" caption="Character class, not a footnote" >}}\n'
        "```sh\ngrep '[^n1]' file\n```\n"
        "{{< /eg >}}\n\n"
        '{{< tbl num="1-2" caption="Inline code is not a footnote" >}}\n'
        "| a |\n| --- |\n| `[^n2]` and [^undefined] |\n"
        "{{< /tbl >}}\n\n"
        "[^n1]: First note.\n[^n2]: Second note.\n"
    )
    with tempfile.TemporaryDirectory(prefix="oink-components-book-footnote-") as temp:
        source = Path(temp)
        create_site(source, body)
        result = build(hugo, source, source / "public")
        if result.returncode != 0:
            return [f"Book footnote fixture failed: {result.stdout}{result.stderr}"]
        page = (source / "public/book/page/index.html").read_text(encoding="utf-8")
        start = page.index('id="tab_notes"')
        figure = page[start : page.index("</figure>", start)]
        for marker in ('href="#fn:1"', 'href="#fn:2"', 'class="footnote-ref"'):
            require(marker in figure, f"native numbered table lost {marker}", errors)
        require("[^n1]" not in figure, "native numbered table printed a literal footnote reference", errors)
        require("[^undefined]" in page, "an undefined footnote reference stopped rendering as text", errors)
        require(page.count('class="footnotes"') == 1, "the page rendered more than one footnote list", errors)
    return errors


def check_invalid_contributors(hugo: str) -> list[str]:
    errors: list[str] = []
    cases = (
        ("role-type", "items:\n  - github: pgsty\n    role: false\n", "role for \"pgsty\" must be a string"),
        ("url-type", "items:\n  - github: pgsty\n    url: 0\n", "url for \"pgsty\" must be a string"),
        ("avatar-empty", 'items:\n  - github: pgsty\n    avatar: ""\n', "avatar for \"pgsty\" must not be empty"),
        ("duplicate", "items:\n  - github: pgsty\n  - github: PGSTY\n", "duplicate GitHub handle"),
    )
    for name, data, expected in cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-components-contributors-invalid-{name}-") as temp:
            source = Path(temp)
            create_site(source, "{{< contributors >}}")
            write(source / "data/contributors.yaml", data)
            result = build(hugo, source, source / "public")
            output = result.stdout + result.stderr
            require(result.returncode == 0,
                    f"invalid contributors case {name} stopped the ordinary build", errors)
            require(expected in output, f"invalid contributors case {name} did not report {expected!r}", errors)
            require((source / "public/book/page/index.html").is_file(),
                    f"invalid contributors case {name} emitted no safe page output", errors)
    return errors


def check_ddia_compatibility(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-book-ddia-") as temp:
        source = Path(temp)
        create_site(
            source,
            '{{< fig num="2-1" id="office_2003" src="/figure.png" title="Legacy caption" '
            'class="legacy wide" link="https://example.org/source" width="640" height="480" />}}',
        )
        result = build(hugo, source, source / "public")
        if result.returncode != 0:
            return [f"DDIA-compatible fig fixture failed: {result.stdout}{result.stderr}"]
        page = (source / "public/book/page/index.html").read_text(encoding="utf-8")
        for marker in (
            'id="office_2003"',
            # `fig` carries the shared image-figure base class as well, so the
            # shortcode and the native numbered form style identically.
            'class="td-figure td-book-figure td-book-figure--fig legacy wide"',
            'href="https://example.org/source"',
            'src="/figure.png"',
            'alt="Legacy caption"',
            'width="640"',
            'height="480"',
            "Figure 2-1",
            "Legacy caption",
        ):
            require(marker in page, f"DDIA parameter compatibility lost {marker}", errors)
    return errors


def check_rss_output(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-book-rss-") as temp:
        source = Path(temp)
        write(
            source / "hugo.yaml",
            base_config().replace("disableKinds: [home, RSS, sitemap, taxonomy, term]", "disableKinds: [home, sitemap, taxonomy, term]").replace("section: [HTML]", "section: [HTML, RSS]"),
        )
        write(source / "content/book/_index.md", "---\ntitle: Book\ntype: book\ncascade:\n  type: book\n---\n")
        write(source / "data/contributors.yaml", "items:\n  - github: pgsty\n    role: Theme fixture\n")
        write(
            source / "content/book/page.md",
            """---
title: RSS page
---
{{< fig num="1" src="/x.png" caption="Caption" />}}
{{< tbl num="1" caption="Rows" >}}| A | B |
| - | - |
| 1 | 2 |{{< /tbl >}}
{{< eq >}}a+b{{< /eq >}}
{{< eq num="1" >}}x+y{{< /eq >}}
{{< eg num="1" caption="Sample" >}}
```sql
SELECT 1;
```
{{< /eg >}}
{{< contributors >}}
{{< xref fig="1" />}}
before{{< book-toc >}}after

<!--more-->
""",
        )
        result = build(hugo, source, source / "public")
        if result.returncode != 0:
            return [f"Book RSS fixture failed: {result.stdout}{result.stderr}"]
        path = source / "public/book/index.xml"
        require(path.exists(), "Book RSS fixture emitted no page output", errors)
        if path.exists():
            feed = ET.fromstring(path.read_text(encoding="utf-8"))
            rss = feed.findtext("channel/item/description", "")
            for marker in ("Figure 1", "Caption", "Table 1", "Rows", "<table", "<math",
                           "Equation 1", "Example 1", "Sample", "SELECT", "<ul>",
                           "https://github.com/pgsty", 'href="#fig-1"', "beforeafter"):
                require(marker in rss, f"Book RSS fallback lost {marker}", errors)
            for marker in ("**Figure", "**Table", "$$", "| A |", "[Figure 1]", "<script", "<button", "<nav"):
                require(marker not in rss, f"Book RSS output leaked {marker}", errors)
            require(feed.find("channel/item/pubDate") is None,
                    "undated Book page emitted a fabricated publication date", errors)
    return errors


def check_validator_regressions() -> list[str]:
    errors: list[str] = []
    documents = {
        "/book/one/": parse_html(
            '<figure id="shared" data-td-book-kind="fig" data-td-book-num="1"><img src="x" alt=""><figcaption>Figure 1</figcaption></figure>'
            '<a class="td-book-xref td-book-xref--fig" data-td-book-kind="fig" data-td-book-num="2" href="#shared">Figure 2</a>'
            '<a class="td-book-xref" href="#missing">missing</a>'
        ),
        "/book/two/": parse_html(
            '<figure id="shared" data-td-book-kind="fig" data-td-book-num="1"><figcaption>Figure 1</figcaption></figure>'
        ),
    }
    found = "\n".join(validate_documents(documents))
    for marker in ("empty alt", "missing anchor", "does not match target number", "duplicate target id"):
        require(marker in found, f"Book checker no longer detects {marker}", errors)
    return errors


def check_sources() -> list[str]:
    errors: list[str] = []
    source_markers = {
        "layouts/_shortcodes/fig.html": ("register-target.html", "data-td-book-kind", "src", "title", "width", "height"),
        "layouts/_shortcodes/tbl.html": ("register-target.html", "render-block.html", "data-td-book-kind"),
        "layouts/_shortcodes/eq.html": ("scripts/math.html", "data-td-book-kind"),
        "layouts/_shortcodes/xref.html": ("targetPage.RelPermalink", "tdBookAggregate", "data-td-book-num"),
        "layouts/_shortcodes/book-toc.html": ("depth", "drafts", "toc-tree.html", "toc-markdown.html"),
        "layouts/_shortcodes/tabs.html": ("tdTabsGroupSeen", "tdBookAggregate", "$printVariant"),
        "layouts/_shortcodes/eg.html": ("register-target.html", "render-block.html", "data-td-book-kind", "markdown"),
        "layouts/_shortcodes/book-tables.html": ('"kind" "tbl"',),
        "layouts/_shortcodes/book-equations.html": ('"kind" "eq"',),
        "layouts/_shortcodes/book-examples.html": ('"kind" "eg"',),
        "layouts/_partials/content/table-render.html": ("register-target.html", '"kind" "tbl"', "data-td-book-kind"),
        "layouts/_markup/render-image.html": ("register-target.html", '"kind" "fig"', "data-td-book-kind"),
        "layouts/_markup/render-passthrough.html": ("register-target.html", '"kind" "eq"', "data-td-book-kind"),
        "layouts/_markup/render-codeblock.html": ("register-target.html", '"kind" "eg"', "data-td-book-kind"),
        "layouts/_shortcodes/contributors.html": ("contributors/items.html", "contributors/wall.html", "markdown"),
        "layouts/_partials/contributors/items.html": ("github", "duplicate GitHub handle", "avatar"),
        "layouts/_partials/contributors/wall.html": ("td-contributor-wall", "data-td-contributor-count", "loading=\"lazy\"", "avatar--placeholder"),
        "layouts/_partials/book/pages.html": ("nav-flatten.html", "IsDescendant"),
        "layouts/_partials/book/print.html": ("book/pages.html", "no_print", 'partialCached "print/page-content.html"', "$content.book", "namespace-print-headings.html", 'Store.Get "hasMath"', "data-td-book-page"),
        "layouts/_partials/book/manifest.json": ("schemaVersion", "baseURL", "aggregateId", "book/pages.html", "tdBookTargetOrder", "tdBookXrefs", "OutputFormats.Get"),
        "layouts/index.bookmanifest.json": ("book/manifest.json",),
        "layouts/book/list.bookmanifest.json": ("book/manifest.json",),
        "layouts/_partials/book/toc-headings.html": ("htmlUnescape",),
        "layouts/_partials/print/page-content.html": ("tdBookAggregate", "static-image-output.html", 'dict "plain" $plain "book" $book'),
        "layouts/_partials/print/content.html": ('partialCached "print/page-content.html"', "namespace-print-headings.html"),
        "layouts/_partials/print/render.html": ('partialCached "print/page-content.html"', "namespace-print-headings.html"),
        "layouts/_partials/book/namespace-print-headings.html": ("Fragments.Identifiers", "aggregate-heading-anchor.html", "RelPermalink", "fnref[0-9]*|fn"),
        "layouts/_partials/book/sidebar-headings.html": ("Fragments.ToHTML", "sidebar_headings"),
        "layouts/_partials/shell/config.html": ('slice "docs" "book" "blog" "swagger"',),
        "layouts/_td-content.html": ('ne .Type "book"', "reading-time.html"),
        "assets/scss/td/_book.scss": ("forced-colors", "@media print", "break-inside", "td-book-draft", "td-book-content--normal", "&--eg", "flex-wrap: wrap", "overflow-wrap: anywhere"),
        "assets/scss/td/_contributors.scss": ("auto-fill", "forced-colors", "@media print"),
    }
    for relative, markers in source_markers.items():
        path = ROOT / relative
        require(path.exists(), f"Book source is missing: {relative}", errors)
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        for marker in markers:
            require(marker in source, f"{relative} lacks {marker}", errors)
    page_content = (ROOT / "layouts/_partials/print/page-content.html").read_text(encoding="utf-8")
    require(
        "namespace-print-headings.html" not in page_content,
        "single-page Print content still namespaces page-local anchors",
        errors,
    )
    for relative in (
        "layouts/book/single.print.html",
        "layouts/docs/single.print.html",
        "layouts/blog/single.print.html",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        require(
            "namespace-print-headings.html" not in source,
            f"{relative} namespaces single-page Print anchors",
            errors,
        )
    for relative, variant in (
        ("layouts/book/single.print.html", "plain"),
        ("layouts/docs/single.print.html", "plain"),
        ("layouts/blog/single.print.html", "plain"),
        ("layouts/_partials/print/content.html", "plain"),
        ("layouts/_partials/print/render.html", "plain"),
        ("layouts/_partials/book/print.html", "book"),
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        require(f"$content.{variant}" in source
                and '.RelPermalink "book"' not in source
                and '"book" true' not in source,
                f"{relative} does not select {variant} from the shared per-page Print cache", errors)
    require(page_content.count("$page.RenderString") == 2
            and page_content.index('$page.Store.Delete "tdBookAggregate"')
            < page_content.index("$plain := $page.RenderString")
            < page_content.index('$page.Store.Set "tdBookAggregate" true')
            < page_content.index("$book = $page.RenderString"),
            "print/page-content.html does not serialize plain then Book variants", errors)
    book_styles = (ROOT / "assets/scss/td/_book.scss").read_text(encoding="utf-8")
    sidebar_number = re.search(
        r">\s*\.td-book-number\s*\{([^}]*)\}", book_styles, re.DOTALL
    )
    require(sidebar_number is not None, "Book sidebar number rule is missing", errors)
    if sidebar_number is not None:
        rule = sidebar_number.group(1)
        for marker in (
            "flex: 0 0 auto",
            "overflow: visible",
            "overflow-wrap: normal",
            "text-overflow: clip",
            "white-space: nowrap",
        ):
            require(marker in rule, f"Book sidebar number rule lacks {marker}", errors)
    i18n = (ROOT / "i18n/en.yaml").read_text(encoding="utf-8")
    for key in ("book_figure", "book_table", "book_equation", "book_example", "book_toc", "book_draft", "book_draft_notice", "contributors_count"):
        require(re.search(rf"^{key}:", i18n, re.M) is not None, f"English i18n lacks {key}", errors)
    return errors


def check_publication_helpers() -> list[str]:
    """Pin packager path and remote-resource safety without external tools."""
    errors: list[str] = []

    def load(name: str, relative: str):
        spec = importlib.util.spec_from_file_location(name, ROOT / relative)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load {relative}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    try:
        epub = load("oink_book_epub", "bin/book-epub.py")
        pdf = load("oink_book_pdf", "bin/book-pdf.py")
        expected = (Path(tempfile.gettempdir()) / "publication-public/docs2/file.png").resolve()
        for label, module in (("EPUB", epub), ("PDF", pdf)):
            actual = module.public_file(
                Path(tempfile.gettempdir()) / "publication-public",
                "/docs2/file.png",
                "/docs",
            )
            require(actual == expected, f"{label} base-path stripping ignores path-segment boundaries", errors)

        pages = [{"path": "/chapter", "html": "/docs/chapter/", "aggregateId": "pg-1"}]
        renderer = epub.BookHTML(
            public=ROOT,
            base_url="https://example.org/docs/",
            pages=pages,
            anchor_owners={},
            allow_remote_resources=True,
        )
        for value, tag in (("file:///etc/passwd", "img"), ("https://cdn.example/app.js", "script")):
            try:
                renderer._resource(value, tag)
                errors.append(f"EPUB accepted unsafe remote resource <{tag}> {value}")
            except ValueError:
                pass
        require(
            renderer._resource("https://cdn.example/poster.jpg", "img")
            == "https://cdn.example/poster.jpg",
            "EPUB remote-media opt-in rejected a passive image",
            errors,
        )
        try:
            renderer._chunk("/missing", "self-test")
            errors.append("EPUB missing manifest owner did not fail cleanly")
        except ValueError:
            pass
        renderer.feed(
            '<iframe src="https://cdn.example/frame"></iframe>'
            '<object data="https://cdn.example/object"></object>'
            '<embed src="https://cdn.example/embed">'
        )
        require(
            not any(tag in renderer.html() for tag in ("<iframe", "<object", "<embed")),
            "EPUB kept active embedded content",
            errors,
        )

        with tempfile.TemporaryDirectory(prefix="oink-publication-safety-") as temp:
            root = Path(temp)
            document = root / "index.html"
            for source in (
                '<script src="https://cdn.example/app.js"></script>',
                '<img src="file:///etc/passwd" alt="">',
            ):
                write(document, source)
                try:
                    pdf.validate_resources(
                        document,
                        public=root,
                        document_route="/docs/print/",
                        base_path="/docs",
                        allow_remote_resources=True,
                    )
                    errors.append(f"PDF accepted unsafe resource fixture: {source}")
                except ValueError:
                    pass
            write(document, '<img src="https://cdn.example/poster.jpg" alt="">')
            pdf.validate_resources(
                document,
                public=root,
                document_route="/docs/print/",
                base_path="/docs",
                allow_remote_resources=True,
            )
    except (OSError, RuntimeError, ValueError) as error:
        errors.append(f"publication helper self-test failed: {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--public", type=Path)
    parser.add_argument("--site-public", type=Path)
    args = parser.parse_args()

    if args.public is not None and args.site_public is not None:
        parser.error("--public and --site-public are mutually exclusive")

    if args.site_public is not None:
        errors = check_consumer_public(args.site_public)
        if errors:
            print("consumer Book checks failed:")
            for error in errors:
                print(f"  {error}")
            return 1
        print("consumer Book checks passed")
        return 0

    if args.public is None:
        with tempfile.TemporaryDirectory(prefix="oink-components-book-") as temp:
            public = Path(temp) / "public"
            result = build(args.hugo, FIXTURE, public)
            if result.returncode != 0:
                print("Book fixture failed to build:")
                print(result.stdout + result.stderr)
                return 1
            errors = check_example(public)
    else:
        errors = check_example(args.public)

    errors += (
        check_sidebar_headings(args.hugo)
        + check_toc_heading_entities(args.hugo)
        + check_toc_drafts(args.hugo)
        + check_print_store_isolation(args.hugo)
        + check_home_manifest(args.hugo)
        + check_reading_time(args.hugo)
        + check_invalid_components(args.hugo)
        + check_invalid_number_outputs(args.hugo)
        + check_footnotes(args.hugo)
        + check_invalid_contributors(args.hugo)
        + check_ddia_compatibility(args.hugo)
        + check_rss_output(args.hugo)
        + check_validator_regressions()
        + check_publication_helpers()
        + check_sources()
    )
    if errors:
        print("Book checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Book checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
