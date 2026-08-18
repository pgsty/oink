#!/usr/bin/env python3
"""Validate GitHub release metadata, lists, and release assets."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
MAIN_SCRIPT = re.compile(r'<script src="(?P<src>/js/page-[^"]+\.js)"')


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(
    hugo: str,
    source: Path,
    destination: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [hugo, "--source", str(source), "--logLevel", "warn"]
    if destination is not None:
        command.extend(["--destination", str(destination)])
    return subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def create_site(root: Path, config_extra: str = "") -> None:
    (root / "themes").mkdir(parents=True)
    (root / "themes/oink").symlink_to(ROOT, target_is_directory=True)
    write(
        root / "hugo.yaml",
        """baseURL: https://example.org/
title: release fixture
theme: oink
defaultContentLanguage: en
buildFuture: true
disableKinds: [RSS, sitemap, taxonomy, term]
outputs:
  page: [HTML]
  section: [HTML]
params:
  offline_search: false
  ui:
    pager_types: []
"""
        + config_extra,
    )
    write(
        root / "content/docs/_index.md",
        """---
title: Docs
type: docs
cascade:
  type: docs
---
""",
    )


class ReleaseIndexParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, dict[str, str | None]]] = []
        self.rows: list[dict[str, str]] = []
        self.groups: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        self.stack.append((tag, values))
        classes = set((values.get("class") or "").split())
        if tag == "li" and "td-release-index__item" in classes:
            self.rows.append(
                {
                    "product": values.get("data-td-release-product") or "",
                    "href": "",
                    "version": "",
                }
            )
        if tag == "a" and "td-release-index__version" in classes and self.rows:
            self.rows[-1]["href"] = values.get("href") or ""

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                self.stack = self.stack[:index]
                break

    def handle_data(self, data: str) -> None:
        classes = {
            name
            for _, attrs in self.stack
            for name in (attrs.get("class") or "").split()
        }
        if "td-release-index__version" in classes and self.rows:
            self.rows[-1]["version"] += data.strip()
        if "td-release-index__product" in classes and data.strip():
            self.groups.append(data.strip())


def card_fragment(source: str) -> str:
    match = re.search(r'<aside class="td-release-card".*?</aside>', source, re.S)
    return match.group(0) if match else ""


def bundle_path(source: str) -> str:
    match = MAIN_SCRIPT.search(source)
    return match.group("src") if match else ""


def check_example(public: Path) -> list[str]:
    errors: list[str] = []
    paths = {
        name: public / f"blog/release/{name}/index.html"
        for name in (
            "expanded",
            "shorthand",
            "pig-1.9.0",
            "pig-1.10.0",
            "mcli-20260813",
        )
    }
    for name, path in paths.items():
        require(path.exists(), f"release fixture output is missing: {name}", errors)
    if not all(path.exists() for path in paths.values()):
        return errors

    expanded = paths["expanded"].read_text(encoding="utf-8")
    shorthand = paths["shorthand"].read_text(encoding="utf-8")
    require(card_fragment(expanded), "expanded release card is missing", errors)
    require(
        card_fragment(expanded) == card_fragment(shorthand),
        "expanded and shorthand release cards are not byte-identical",
        errors,
    )

    pig = paths["pig-1.10.0"].read_text(encoding="utf-8")
    expected_links = (
        "https://github.com/pgsty/pig/releases/tag/v1.10.0",
        "https://github.com/pgsty/pig/archive/refs/tags/v1.10.0.tar.gz",
        "https://github.com/pgsty/pig/archive/refs/tags/v1.10.0.zip",
        "https://github.com/pgsty/pig/releases/download/v1.10.0/checksums.txt",
        "https://github.com/pgsty/pig/compare/v1.9.0...v1.10.0",
        "https://github.com/pgsty/pig",
    )
    for url in expected_links:
        require(f'href="{url}"' in card_fragment(pig), f"release card lost {url}", errors)
    require("data-td-asset-list" in pig, "release asset HTML is missing", errors)
    require(
        'class="td-asset-list__table-wrap" tabindex="0" role="region"'
        in pig,
        "release asset scroll region is not keyboard focusable",
        errors,
    )
    require(
        '<th scope="col" aria-label="Copy checksum"></th>' in pig,
        "release asset action header lacks a non-overflowing accessible name",
        errors,
    )
    require("SHA-256" in pig, "release asset algorithm badge is missing", errors)
    require(
        all(marker in pig for marker in (">arm64<", ">amd64<", "data-td-asset-copy-all")),
        "release asset inference or copy controls are missing",
        errors,
    )
    hashes = (
        "e3a339fefdd2203825d15438b52f18e729547eb88dae014212a46006a9bd47d1",
        "34ce29d75ef9f669f3bf832cc812ae082abda7320ee2b2336ea61e701b9b67f8",
    )
    for checksum in hashes:
        require(f'data-td-asset-hash="{checksum}"' in pig, "HTML lost a full copy hash", errors)
    visible_hashes = re.findall(
        r'<code aria-label="[0-9A-Fa-f]+">([^<]+)</code>', pig
    )
    require(
        visible_hashes == ["e3a339fe…47d1", "34ce29d7…67f8"],
        f"HTML visual hashes are not truncated as expected: {visible_hashes}",
        errors,
    )

    base = (public / "fixtures/release-assets-base/index.html").read_text(encoding="utf-8")
    require(
        'href="https://downloads.example.org/releases/stable/OINK%20manual%20%28final%29.zip"'
        in base,
        "asset filename is not encoded as one URL path segment",
        errors,
    )
    require(">Linux<" in base and ">amd64<" in base, "asset OS/arch badges are missing", errors)

    asset_bundle = bundle_path(pig)
    plain = paths["pig-1.9.0"].read_text(encoding="utf-8")
    plain_bundle = bundle_path(plain)
    require(asset_bundle and plain_bundle, "fixture pages lost their feature bundle", errors)
    require(asset_bundle != plain_bundle, "hasAssetList did not change the bundle key", errors)
    if asset_bundle:
        script = public / asset_bundle.lstrip("/")
        require(script.exists(), "asset-list bundle file is missing", errors)
        if script.exists():
            require("OinkAssetList" in script.read_text(encoding="utf-8"), "asset-list runtime was not bundled", errors)

    markdown = (public / "blog/release/pig-1.10.0/index.md").read_text(encoding="utf-8")
    for checksum in hashes:
        require(checksum in markdown, "Markdown asset table lost a full hash", errors)
    for marker in ("| File | Checksum |", "https://github.com/pgsty/pig/releases/download/v1.10.0/", "SHA-256"):
        require(marker in markdown, f"Markdown asset table lost {marker}", errors)
    for marker in ("td-asset", "data-td-asset", "<table", "<button"):
        require(marker not in markdown, f"Markdown asset table contains {marker}", errors)

    print_path = public / "_print/blog/release/pig-1.10.0/index.html"
    require(print_path.exists(), "release page print output is missing", errors)
    if print_path.exists():
        print_source = print_path.read_text(encoding="utf-8")
        for checksum in hashes:
            require(checksum in print_source, "print asset table lost a full hash", errors)
        for marker in ("data-td-asset-copy", "td-asset-list__copy-all"):
            require(marker not in print_source, f"print asset table contains {marker}", errors)
        require("td-release-card__link" not in print_source, "print used interactive release-card links", errors)

    index_path = public / "blog/release/index.html"
    parser = ReleaseIndexParser()
    parser.feed(index_path.read_text(encoding="utf-8"))
    actual = [row["href"] for row in parser.rows]
    expected = [
        "/blog/release/mcli-20260813/",
        "/blog/release/pig-1.10.0/",
        "/blog/release/pig-1.9.0/",
        "/blog/release/shorthand/",
        "/blog/release/expanded/",
    ]
    require(actual == expected, f"release index order is {actual}, expected {expected}", errors)
    require(parser.groups == [], "default release list unexpectedly groups products", errors)
    return errors


def check_algorithms_and_rss(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-release-formats-") as temp:
        site = Path(temp)
        create_site(site)
        blocks = (
            ("md5", "a" * 32, "MD5"),
            ("sha1", "b" * 40, "SHA-1"),
            ("sha256", "c" * 64, "SHA-256"),
            ("sha512", "d" * 128, "SHA-512"),
        )
        body = ["---", "title: Algorithms", "outputs: [HTML]", "---", ""]
        for algorithm, checksum, _ in blocks:
            body.extend(
                [
                    f'{{{{< release-assets base="https://example.org/files" algo="{algorithm}" >}}}}',
                    f"{checksum}  {algorithm}.zip",
                    "{{< /release-assets >}}",
                    "",
                ]
            )
        write(site / "content/docs/algorithms.md", "\n".join(body))
        result = run(hugo, site)
        if result.returncode != 0:
            errors.append(f"algorithm fixture failed: {result.stdout}{result.stderr}")
        else:
            source = (site / "public/docs/algorithms/index.html").read_text(encoding="utf-8")
            for _, _, label in blocks:
                require(label in source, f"asset table did not recognize {label}", errors)

    with tempfile.TemporaryDirectory(prefix="oink-components-release-rss-") as temp:
        site = Path(temp)
        create_site(site)
        config = (site / "hugo.yaml").read_text(encoding="utf-8")
        write(
            site / "hugo.yaml",
            config.replace("disableKinds: [RSS,", "disableKinds: [").replace(
                "page: [HTML]", "page: [RSS]"
            ),
        )
        write(
            site / "layouts/docs/single.rss.xml",
            '{{- .Store.Set "tdOutputFormat" "rss" -}}<fixture>{{ .RenderShortcodes }}</fixture>\n',
        )
        write(
            site / "content/docs/rss.md",
            """---
title: RSS release
date: 2026-08-14
outputs: [RSS]
release:
  version: 2.0.0
  repo: pgsty/oink
---

{{< release-card >}}

{{< release-assets >}}
eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee  oink.zip
{{< /release-assets >}}
""",
        )
        result = run(hugo, site)
        if result.returncode != 0:
            errors.append(f"release RSS fixture failed: {result.stdout}{result.stderr}")
        else:
            outputs = list((site / "public/docs").rglob("*.xml"))
            require(len(outputs) == 1, "release RSS fixture did not emit one page", errors)
            if outputs:
                source = outputs[0].read_text(encoding="utf-8")
                for marker in (
                    "https://github.com/pgsty/oink/releases/tag/v2.0.0",
                    "| File | Checksum |",
                    "e" * 64,
                ):
                    require(marker in source, f"RSS release output lost {marker}", errors)
                for marker in ("td-release-card__link", "data-td-asset", "<button"):
                    require(marker not in source, f"RSS release output contains {marker}", errors)
    return errors


def check_grouping(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-release-groups-") as temp:
        site = Path(temp)
        create_site(site)
        write(
            site / "content/blog/releases/_index.md",
            """---
title: Product releases
type: blog
layout: releases
release_group_by_product: true
release_products: [pig, mcli]
cascade:
  type: blog
---
""",
        )
        records = (
            ("pig-nine", "pig", "1.9.0", "2026-08-14", 999),
            ("pig-ten", "pig", "1.10.0", "2026-08-14", -999),
            ("mcli", "mcli", "20260815", "2026-08-15", 1),
            ("console", "console", "3.0.0", "2026-08-16", 1),
        )
        for name, product, version, date, weight in records:
            write(
                site / f"content/blog/releases/{name}.md",
                f"""---
title: {name}
date: {date}
weight: {weight}
release:
  product: {product}
  version: '{version}'
  repo: pgsty/oink
  date: {date}
---
""",
            )
        result = run(hugo, site)
        if result.returncode != 0:
            errors.append(f"grouped release fixture failed: {result.stdout}{result.stderr}")
            return errors
        parser = ReleaseIndexParser()
        parser.feed((site / "public/blog/releases/index.html").read_text(encoding="utf-8"))
        require(parser.groups == ["mcli", "pig"], f"release product groups are {parser.groups}", errors)
        require(
            [row["href"] for row in parser.rows]
            == [
                "/blog/releases/mcli/",
                "/blog/releases/pig-ten/",
                "/blog/releases/pig-nine/",
            ],
            "release product filter/group order is wrong",
            errors,
        )
        require(
            all(row["product"] in {"mcli", "pig"} for row in parser.rows),
            "release product filter leaked an excluded product",
            errors,
        )
    return errors


INVALID_CASES = (
    (
        "release-bad-shorthand",
        "release: https://gitlab.com/pgsty/oink/releases/tag/v1.0.0",
        "{{< release-card >}}",
        "release shorthand must match",
    ),
    ("release-missing-version", "release:\n  repo: pgsty/oink", "{{< release-card >}}", "release.version is required"),
    ("release-missing-repo", "release:\n  version: 1.0.0", "{{< release-card >}}", "release.repo is required"),
    ("release-bad-repo", "release:\n  version: 1.0.0\n  repo: bad", "{{< release-card >}}", "owner/repository pair"),
    ("release-unknown", "release:\n  version: 1.0.0\n  repo: pgsty/oink\n  url: bad", "{{< release-card >}}", "unsupported field"),
    ("release-date", "release:\n  version: 1.0.0\n  repo: pgsty/oink\n  date: never", "{{< release-card >}}", "release.date must be a valid date"),
    ("release-scalar", "release: true", "{{< release-card >}}", "must be a map or GitHub release URL"),
    ("release-card-param", "release:\n  version: 1.0.0\n  repo: pgsty/oink", '{{< release-card version="1.0.0" >}}', "accepts no parameters"),
    ("asset-bad-line", "", '{{< release-assets base="/files" >}}\nnot-a-sum\n{{< /release-assets >}}', "line 2 must be"),
    ("asset-bad-length", "", '{{< release-assets base="/files" >}}\naaaa  file.zip\n{{< /release-assets >}}', "unsupported hex length 4"),
    ("asset-mixed", "", '{{< release-assets base="/files" >}}\n' + "a" * 32 + "  old.zip\n" + "b" * 64 + "  new.zip\n{{< /release-assets >}}", "mixes checksum algorithms"),
    ("asset-override", "", '{{< release-assets base="/files" algo="sha256" >}}\n' + "a" * 32 + "  old.zip\n{{< /release-assets >}}", "conflicts with algo"),
    ("asset-dual-source", "", '{{< release-assets base="/files" src="release/shared-checksums.txt" >}}\n' + "a" * 64 + "  file.zip\n{{< /release-assets >}}", "mutually exclusive"),
    ("asset-missing-source", "", "{{< release-assets >}}\n" + "a" * 64 + "  file.zip\n{{< /release-assets >}}", "requires release front matter or base"),
    ("asset-bad-src", "", '{{< release-assets base="/files" src="missing.txt" >}}{{< /release-assets >}}', "was not found"),
    ("asset-release-base", "release:\n  version: 1.0.0\n  repo: pgsty/oink", '{{< release-assets base="/files" >}}\n' + "a" * 64 + "  file.zip\n{{< /release-assets >}}", "base is only valid without release front matter"),
    ("asset-path", "", '{{< release-assets base="/files" >}}\n' + "a" * 64 + "  path/file.zip\n{{< /release-assets >}}", "filename must be one path segment"),
    ("asset-scheme", "", '{{< release-assets base="javascript:alert(1)" >}}\n' + "a" * 64 + "  file.zip\n{{< /release-assets >}}", "base URL must use http or https"),
    ("asset-protocol-relative", "", '{{< release-assets base="//example.org/files" >}}\n' + "a" * 64 + "  file.zip\n{{< /release-assets >}}", "protocol-relative"),
    ("asset-positional", "", '{{< release-assets "/files" >}}\n' + "a" * 64 + "  file.zip\n{{< /release-assets >}}", "accepts named parameters only"),
    ("asset-unknown", "", '{{< release-assets base="/files" color="red" >}}\n' + "a" * 64 + "  file.zip\n{{< /release-assets >}}", "unsupported parameter"),
)


def check_invalid(hugo: str) -> list[str]:
    errors: list[str] = []
    for name, front_matter, body, expected in INVALID_CASES:
        with tempfile.TemporaryDirectory(prefix=f"oink-components-{name}-") as temp:
            site = Path(temp)
            create_site(site)
            write(
                site / "content/docs/invalid.md",
                f"---\ntitle: Invalid {name}\ndate: 2026-08-14\n{front_matter}\n---\n\n{body}\n",
            )
            result = run(hugo, site)
            output = result.stdout + result.stderr
            require(result.returncode != 0, f"invalid case {name} unexpectedly built", errors)
            require(expected in output, f"invalid case {name} did not report {expected!r}", errors)
            require("content/docs/invalid.md:" in output, f"invalid case {name} lost its source position", errors)
    return errors


def check_sources() -> list[str]:
    errors: list[str] = []
    scripts = (ROOT / "layouts/_partials/scripts.html").read_text(encoding="utf-8")
    shortcode = (ROOT / "layouts/_shortcodes/release-assets.html").read_text(encoding="utf-8")
    parser = (ROOT / "layouts/_partials/release/assets-parse.html").read_text(encoding="utf-8")
    styles = (ROOT / "assets/scss/td/_release.scss").read_text(encoding="utf-8")
    require('Page.Store.Set "hasAssetList" true' in shortcode, "release-assets never sets its runtime flag", errors)
    require('$hasAssetList' in scripts and 'resources.Get "js/asset-list.js"' in scripts, "asset-list runtime is not conditionally wired", errors)
    require(
        "$hasAssetList -}}" in scripts
        and 'range . }}{{ $bundleKey = printf "%s|%s" $bundleKey .Name }}' in scripts,
        "asset-list is not appended under its flag into the derived bundle key",
        errors,
    )
    require("line %d" in parser, "asset parser errors do not retain line numbers", errors)
    for marker in ("@media print", "@media (forced-colors: active)"):
        require(marker in styles, f"release/asset styles lack {marker}", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--public", type=Path)
    args = parser.parse_args()

    if args.public is None:
        with tempfile.TemporaryDirectory(prefix="oink-components-release-example-") as temp:
            public = Path(temp) / "public"
            result = run(args.hugo, EXAMPLE, public)
            if result.returncode != 0:
                print("release fixture failed to build:")
                print(result.stdout + result.stderr)
                return 1
            errors = check_example(public)
    else:
        errors = check_example(args.public)

    errors += (
        check_algorithms_and_rss(args.hugo)
        + check_grouping(args.hugo)
        + check_invalid(args.hugo)
        + check_sources()
    )
    if errors:
        print("release/asset checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("release/asset checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
