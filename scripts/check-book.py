#!/usr/bin/env python3
"""Validate the PRD 5 Book component contract and output matrix."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"


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
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
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
        self._figure: dict[str, object] | None = None
        self._figure_caption = False
        self._xref: dict[str, str] | None = None
        self._sidebar_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
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
                    "kind": values.get("data-book-kind") or "",
                    "num": values.get("data-book-num") or "",
                    "text": "",
                }
        if tag == "section" and values.get("data-book-page"):
            self.book_pages.append(values["data-book-page"] or "")
        if tag == "figure" and values.get("data-book-kind"):
            target = {
                "id": values.get("id") or "",
                "kind": values.get("data-book-kind") or "",
                "num": values.get("data-book-num") or "",
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
                kind in {"fig", "tbl", "eq"},
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


def check_example(public: Path) -> list[str]:
    errors: list[str] = []
    paths = {
        "root": public / "book/index.html",
        "one": public / "book/chapter-one/index.html",
        "two": public / "book/chapter-two/index.html",
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
    require(set(documents) == {"/book/", "/book/chapter-one/", "/book/chapter-two/"}, "Book fixture page set changed", errors)

    one = documents.get("/book/chapter-one/")
    two = documents.get("/book/chapter-two/")
    root = documents.get("/book/")
    if one and two and root:
        require(one.sidebar_links[:3] == ["/book/", "/book/chapter-one/", "/book/chapter-two/"], "Book sidebar order changed", errors)
        require(one.pager == {"prev": "/book/", "next": "/book/chapter-two/"}, "Book pager does not follow sidebar pre-order", errors)
        require(two.pager == {"prev": "/book/chapter-one/"}, "last Book page pager is wrong", errors)
        require(two.has_sidebar_headings, "active Book page has no sidebar heading branch", errors)
        require(set(one.targets) == {"office_2003", "tbl-1-1", "eq-1.1"}, "numbered target registry changed", errors)
        figure = one.targets.get("office_2003")
        if figure:
            images = figure["images"]
            require(len(images) == 1, "fixture figure image is missing", errors)
            if images:
                image = images[0]
                require(image.get("src") == "/icons/logo.svg", "fixture figure src changed", errors)
                require(image.get("width") == "120" and image.get("height") == "120", "figure dimensions were lost", errors)

    toc = re.search(r'<nav class="td-book-toc[\s\S]*?</nav>', source["root"])
    require(toc is not None, "Book table of contents is missing", errors)
    if toc:
        toc_source = toc.group(0)
        for marker in ("/book/chapter-one/", "/book/chapter-two/", "#chapter-details", "#stable-heading", "#shared-heading"):
            require(marker in toc_source, f"depth-three Book ToC lost {marker}", errors)
        for marker in ("/docs/", "/blog/", "/landing-demo/"):
            require(marker not in toc_source, f"Book ToC escaped its root through {marker}", errors)
        require("<ol class=td-book-toc__headings" in toc_source or '<ol class="td-book-toc__headings' in toc_source, "Book ToC lost heading lists", errors)
        require("<ol class=td-book-toc__headings><ol" not in toc_source, "Book ToC contains an empty wrapper list", errors)

    for marker in (
        'class="td-book-figures td-book-figures--fig"',
        "Figure 1-1",
        "/book/chapter-one/#office_2003",
        'class="td-book-figures td-book-figures--tbl"',
        "Table 1-1",
    ):
        require(marker in source["root"], f"Book figure list lost {marker}", errors)
    for marker in ("td-book-draft-badge", "td-book-draft", "data-td-book-headings", "#stable-heading"):
        require(marker in source["two"], f"draft/sidebar output lost {marker}", errors)
    for marker in ("td-table-scroll", 'class="katex-display"', "third_party/katex/katex.min."):
        require(marker in source["one"], f"interactive Book page lost {marker}", errors)

    for marker in (
        "**Figure 1-1.** A stable\\, manually numbered figure\\.",
        "![OINK mark used as a fixture](/icons/logo.svg)",
        "**Table 1-1.** Output behavior by surface\\.",
        "**Equation 1.1.** A direct ToMath escape hatch\\.",
        "[the stable heading](/book/chapter-two/#stable-heading)",
    ):
        require(marker in source["one_md"], f"Markdown Book output lost {marker}", errors)
    for forbidden in ("<figure", "td-book-figure", "katex-html", "td-table-scroll"):
        require(forbidden not in source["one_md"], f"Markdown Book output leaked {forbidden}", errors)
    for marker in ("- [1 Numbered evidence]", "  - [Chapter details]", "- [Figure 1-1]", "- [Table 1-1]"):
        require(marker in source["root_md"], f"Markdown Book index lost {marker}", errors)

    require("td-table-scroll" not in source["one_print"], "print Book table retained its scroll wrapper", errors)
    for marker in ('id="office_2003"', 'id="tbl-1-1"', 'id="eq-1.1"', "Figure 1-1", "Table 1-1"):
        require(marker in source["one_print"], f"chapter print lost {marker}", errors)
    aggregate = parse_html(source["book_print"])
    require(aggregate.book_pages == ["/book", "/book/chapter-one", "/book/chapter-two"], "whole-Book print order changed", errors)
    duplicate_aggregate_ids = sorted(key for key, count in Counter(aggregate.ids).items() if count > 1)
    require(not duplicate_aggregate_ids, f"whole-Book print contains duplicate IDs: {duplicate_aggregate_ids}", errors)
    for element_id in ("office_2003", "tbl-1-1", "eq-1.1"):
        require(source["book_print"].count(f'id={element_id}') + source["book_print"].count(f'id="{element_id}"') == 1, f"whole-Book print does not preserve one {element_id!r}", errors)
    namespaced_headings = re.findall(r'id="(pg-[0-9a-f]+--(?:stable-heading|shared-heading))"', source["book_print"])
    require(len(namespaced_headings) == 3, f"whole-Book print did not namespace repeated headings: {namespaced_headings}", errors)
    for heading_id in namespaced_headings:
        require(f'href="#{heading_id}"' in source["book_print"], f"whole-Book print has no local link to {heading_id!r}", errors)
    for marker in ('href="#office_2003"',):
        require(marker in source["book_print"], f"whole-Book print did not localize {marker}", errors)
    for marker in ('id="stable-heading"', 'id="shared-heading"', 'href="#stable-heading"', 'href="#shared-heading"'):
        require(marker not in source["book_print"], f"whole-Book print retained unscoped heading marker {marker}", errors)
    for marker in ("td-pager", "data-td-pager-prev", "data-td-pager-next", "td-table-scroll"):
        require(marker not in source["book_print"], f"whole-Book print retained interactive marker {marker}", errors)
    return errors


def base_config(extra_ui: str = "") -> str:
    return f"""baseURL: https://example.org/
title: Book fixture
theme: {ROOT.name}
defaultContentLanguage: en
disableKinds: [home, RSS, sitemap, taxonomy, term]
outputs:
  page: [HTML]
  section: [HTML]
params:
  ui:
    shell_types: [book]
    sidebar_root_enabled: true
    sidebar_root_menu: false
    pager:
      types: [book]
{extra_ui}"""


def create_site(root: Path, body: str, *, extra_ui: str = "", draft: bool = False) -> None:
    write(root / "hugo.yaml", base_config(extra_ui))
    write(
        root / "content/book/_index.md",
        "---\ntitle: Book\ntype: book\ncascade:\n  type: book\n---\n",
    )
    status = "book_status: draft\n" if draft else ""
    write(root / "content/book/page.md", f"---\ntitle: Page\n{status}---\n\n{body}\n")


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
        ("empty-table", '{{< tbl num="1" >}}{{< /tbl >}}', "requires inner table content"),
        ("bad-width", '{{< fig num="1" src="/x.png" width="0" />}}', "must be a positive integer"),
        ("many-kinds", '{{< xref fig="1" tbl="1" />}}', "accepts only one"),
        ("xref-empty", '{{< xref />}}', "requires fig, tbl, eq, or anchor"),
        ("xref-anchor-text", '{{< xref anchor="heading" />}}', "requires inner link text"),
        ("xref-page", '{{< xref page="missing" anchor="heading" >}}text{{< /xref >}}', "was not found"),
        ("toc-depth", '{{< book-toc depth=4 >}}', "depth must be from 1 through 3"),
        ("toc-drafts", '{{< book-toc drafts="false" >}}', "drafts must be boolean"),
    )
    for name, body, expected in cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-prd5-book-invalid-{name}-") as temp:
            source = Path(temp)
            create_site(source, body)
            result = build(hugo, source, source / "public")
            output = result.stdout + result.stderr
            require(result.returncode != 0, f"invalid Book case {name} unexpectedly built", errors)
            require(expected in output, f"invalid Book case {name} did not report {expected!r}", errors)

    config_cases = (
        ("headings", "    sidebar_headings: 1\n", False, "params.ui.sidebar_headings"),
        ("banner", '    book_draft_banner: "yes"\n', True, "params.ui.book_draft_banner"),
    )
    for name, extra_ui, draft, expected in config_cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-prd5-book-config-{name}-") as temp:
            source = Path(temp)
            create_site(source, "## Heading\n", extra_ui=extra_ui, draft=draft)
            result = build(hugo, source, source / "public")
            output = result.stdout + result.stderr
            require(result.returncode != 0, f"invalid Book config {name} unexpectedly built", errors)
            require(expected in output, f"invalid Book config {name} did not report {expected!r}", errors)
    return errors


def check_ddia_compatibility(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-prd5-book-ddia-") as temp:
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
            'class="td-book-figure td-book-figure--fig legacy wide"',
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
    with tempfile.TemporaryDirectory(prefix="oink-prd5-book-rss-") as temp:
        source = Path(temp)
        write(
            source / "hugo.yaml",
            base_config().replace("disableKinds: [home, RSS, sitemap, taxonomy, term]", "disableKinds: [home, sitemap, taxonomy, term]").replace("page: [HTML]", "page: [RSS]"),
        )
        write(source / "content/book/_index.md", "---\ntitle: Book\ntype: book\ncascade:\n  type: book\n---\n")
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
{{< xref fig="1" />}}
before{{< book-toc >}}after
""",
        )
        write(
            source / "layouts/book/single.rss.xml",
            '{{- .Store.Set "tdOutputFormat" "rss" -}}<fixture>{{ .RenderShortcodes | safeHTML }}</fixture>\n',
        )
        result = build(hugo, source, source / "public")
        if result.returncode != 0:
            return [f"Book RSS fixture failed: {result.stdout}{result.stderr}"]
        path = source / "public/book/page/index.xml"
        require(path.exists(), "Book RSS fixture emitted no page output", errors)
        if path.exists():
            rss = path.read_text(encoding="utf-8")
            for marker in ("**Figure 1.** Caption", "**Table 1.** Rows", "$$\na+b\n$$", "**Equation 1.**", "[Figure 1](#fig-1)", "beforeafter"):
                require(marker in rss, f"Book RSS fallback lost {marker}", errors)
            for marker in ("<figure", "td-book-", "Book contents", "<nav"):
                require(marker not in rss, f"Book RSS output leaked {marker}", errors)
    return errors


def check_validator_regressions() -> list[str]:
    errors: list[str] = []
    documents = {
        "/book/one/": parse_html(
            '<figure id="shared" data-book-kind="fig" data-book-num="1"><img src="x" alt=""><figcaption>Figure 1</figcaption></figure>'
            '<a class="td-book-xref td-book-xref--fig" data-book-kind="fig" data-book-num="2" href="#shared">Figure 2</a>'
            '<a class="td-book-xref" href="#missing">missing</a>'
        ),
        "/book/two/": parse_html(
            '<figure id="shared" data-book-kind="fig" data-book-num="1"><figcaption>Figure 1</figcaption></figure>'
        ),
    }
    found = "\n".join(validate_documents(documents))
    for marker in ("empty alt", "missing anchor", "does not match target number", "duplicate target id"):
        require(marker in found, f"Book checker no longer detects {marker}", errors)
    return errors


def check_sources() -> list[str]:
    errors: list[str] = []
    source_markers = {
        "layouts/_shortcodes/fig.html": ("register-target.html", "data-book-kind", "src", "title", "width", "height"),
        "layouts/_shortcodes/tbl.html": ("register-target.html", "RenderString", "data-book-kind"),
        "layouts/_shortcodes/eq.html": ("scripts/math.html", "data-book-kind"),
        "layouts/_shortcodes/xref.html": ("targetPage.RelPermalink", "tdBookAggregate", "data-book-num"),
        "layouts/_shortcodes/book-toc.html": ("depth", "drafts", "toc-tree.html", "toc-markdown.html"),
        "layouts/_partials/book/print.html": ("nav-flatten.html", "tdBookAggregate", "namespace-print-headings.html", "data-book-page"),
        "layouts/_partials/book/namespace-print-headings.html": ("Fragments.Identifiers", "aggregate-heading-anchor.html", "RelPermalink"),
        "layouts/_partials/book/sidebar-headings.html": ("Fragments.ToHTML", "sidebar_headings"),
        "layouts/_partials/shell/config.html": ('slice "docs" "book" "blog" "swagger"',),
        "assets/scss/td/_book.scss": ("forced-colors", "@media print", "break-inside", "td-book-draft"),
    }
    for relative, markers in source_markers.items():
        path = ROOT / relative
        require(path.exists(), f"Book source is missing: {relative}", errors)
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        for marker in markers:
            require(marker in source, f"{relative} lacks {marker}", errors)
    i18n = (ROOT / "i18n/en.yaml").read_text(encoding="utf-8")
    for key in ("book_figure", "book_table", "book_equation", "book_lof", "book_lot", "book_toc", "book_draft", "book_draft_notice"):
        require(re.search(rf"^{key}:", i18n, re.M) is not None, f"English i18n lacks {key}", errors)
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
            print("PRD 5 consumer Book checks failed:")
            for error in errors:
                print(f"  {error}")
            return 1
        print("PRD 5 consumer Book checks passed")
        return 0

    if args.public is None:
        with tempfile.TemporaryDirectory(prefix="oink-prd5-book-") as temp:
            public = Path(temp) / "public"
            result = build(args.hugo, EXAMPLE, public)
            if result.returncode != 0:
                print("PRD 5 Book fixture failed to build:")
                print(result.stdout + result.stderr)
                return 1
            errors = check_example(public)
    else:
        errors = check_example(args.public)

    errors += (
        check_invalid_components(args.hugo)
        + check_ddia_compatibility(args.hugo)
        + check_rss_output(args.hugo)
        + check_validator_regressions()
        + check_sources()
    )
    if errors:
        print("PRD 5 Book checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("PRD 5 Book checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
