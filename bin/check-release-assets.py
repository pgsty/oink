#!/usr/bin/env python3
"""Validate GitHub release metadata, lists, and release assets."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import tempfile

from runtime_assets import chunk, referenced_chunks
from test_site import fixture_config_args


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/site"
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
    panic_on_warning: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [hugo, "--source", str(source), "--logLevel", "warn"]
    if source == FIXTURE:
        command.extend(fixture_config_args())
    if destination is not None:
        command.extend(["--destination", str(destination)])
    if panic_on_warning:
        command.append("--panicOnWarning")
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

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        self.stack.append((tag, values))
        classes = set((values.get("class") or "").split())
        if tag == "li" and "td-release-index__item" in classes:
            self.rows.append({"href": "", "name": ""})
        if tag == "a" and "td-release-index__name" in classes and self.rows:
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
        if "td-release-index__name" in classes and self.rows:
            self.rows[-1]["name"] += data.strip()


def card_fragment(source: str) -> str:
    match = re.search(r'<aside class="td-release-card".*?</aside>', source, re.S)
    return match.group(0) if match else ""


def check_example(public: Path) -> list[str]:
    errors: list[str] = []
    paths = {
        name: public / f"blog/release/{name}/index.html"
        for name in (
            "shorthand",
            "plain-note",
            "pig-1.9.0",
            "pig-1.10.0",
            "mcli-20260813",
        )
    }
    for name, path in paths.items():
        require(path.exists(), f"release fixture output is missing: {name}", errors)
    if not all(path.exists() for path in paths.values()):
        return errors

    shorthand = paths["shorthand"].read_text(encoding="utf-8")
    require(card_fragment(shorthand), "the release-URL fixture card is missing", errors)

    pig = paths["pig-1.10.0"].read_text(encoding="utf-8")
    # Four links, all derivable from the release URL alone.
    expected_links = (
        "https://github.com/pgsty/pig/releases/tag/v1.10.0",
        "https://github.com/pgsty/pig/archive/refs/tags/v1.10.0.tar.gz",
        "https://github.com/pgsty/pig/archive/refs/tags/v1.10.0.zip",
        "https://github.com/pgsty/pig",
    )
    for url in expected_links:
        require(f'href="{url}"' in card_fragment(pig), f"release card lost {url}", errors)
    # The map's declared extras went with it: no checksum link the URL cannot
    # name, no comparison the URL does not carry.
    for marker in (
        "releases/download/v1.10.0/checksums.txt",
        "https://github.com/pgsty/pig/compare/",
    ):
        require(marker not in card_fragment(pig), f"release card still carries {marker}", errors)
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

    plain = paths["pig-1.9.0"].read_text(encoding="utf-8")
    require(bool(referenced_chunks(public, pig)), "asset fixture lost its runtime chunks", errors)
    require(bool(referenced_chunks(public, plain)), "plain release lost its runtime chunks", errors)
    asset_runtime = chunk(public, pig, "asset-list")
    require(asset_runtime is not None and asset_runtime.path.is_file(), "asset-list runtime file is missing", errors)
    require(chunk(public, plain, "asset-list") is None, "asset-list runtime leaked onto a plain release", errors)
    if asset_runtime and asset_runtime.path.is_file():
        require("OinkAssetList" in asset_runtime.path.read_text(encoding="utf-8"), "asset-list runtime was not bundled", errors)

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

    # The example's release section is an ordinary blog index published as the
    # compact table, immersive and with the reader's form cycle live; the
    # dedicated releases layout is pinned by check_releases_layout below.
    index_source = (public / "blog/release/index.html").read_text(encoding="utf-8")
    require('data-td-blog-default="table"' in index_source
            and 'class="td-blog-table"' in index_source
            and "data-td-blog-index-toggle" in index_source,
            "the example release index is not the table form with the reader's cycle", errors)
    for href in ("/blog/release/0.5.0/", "/blog/release/pig-1.10.0/", "/blog/release/plain-note/"):
        require(f'href="{href}"' in index_source,
                f"the example release table lost {href}", errors)
    return errors


def check_releases_layout(hugo: str) -> list[str]:
    """The releases layout: `project tag` naming, date-then-version order."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-release-index-") as temp:
        site = Path(temp)
        create_site(site)
        write(
            site / "content/blog/releases/_index.md",
            "---\ntitle: Releases\ntype: blog\nlayout: releases\ncascade:\n  type: blog\n---\n",
        )
        records = (
            ("oink-five", "https://github.com/pgsty/oink/releases/tag/v0.5.0", "2026-08-18"),
            ("mcli", "https://github.com/pgsty/mcli/releases/tag/RELEASE.2026-08-13T00-00-00Z", "2026-08-13"),
            ("pig-ten", "https://github.com/pgsty/pig/releases/tag/v1.10.0", "2026-08-12"),
            ("pig-nine", "https://github.com/pgsty/pig/releases/tag/v1.9.0", "2026-08-12"),
        )
        for name, url, date in records:
            write(
                site / f"content/blog/releases/{name}.md",
                f"---\ntitle: {name}\ndate: {date}\nrelease_url: {url}\n---\n",
            )
        write(
            site / "content/blog/releases/plain.md",
            "---\ntitle: A plain note between releases\ndate: 2026-08-09\n---\n",
        )
        result = run(hugo, site, panic_on_warning=True)
        if result.returncode != 0:
            errors.append(f"releases layout fixture failed: {result.stdout}{result.stderr}")
            return errors
        parser = ReleaseIndexParser()
        parser.feed((site / "public/blog/releases/index.html").read_text(encoding="utf-8"))
        actual = [(row["href"], row["name"]) for row in parser.rows]
        # Date first, then the tag's version within a date. Entries whose
        # release_url parses read as `project tag`; the plain note keeps its
        # own title and its place in the list, and warns about nothing.
        expected = [
            ("/blog/releases/oink-five/", "oink v0.5.0"),
            ("/blog/releases/mcli/", "mcli RELEASE.2026-08-13T00-00-00Z"),
            ("/blog/releases/pig-ten/", "pig v1.10.0"),
            ("/blog/releases/pig-nine/", "pig v1.9.0"),
            ("/blog/releases/plain/", "A plain note between releases"),
        ]
        require(actual == expected, f"releases layout entries are {actual}, expected {expected}", errors)
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
release_url: https://github.com/pgsty/oink/releases/tag/v2.0.0
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


def check_removed_list_keys(hugo: str) -> list[str]:
    """The 0.5 product filter and grouping keys warn and change nothing."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-release-removed-") as temp:
        site = Path(temp)
        create_site(site)
        write(
            site / "content/blog/releases/_index.md",
            """---
title: Product releases
type: blog
layout: releases
release_group_by_product: true
release_products: [pig]
cascade:
  type: blog
---
""",
        )
        write(
            site / "content/blog/releases/pig.md",
            """---
title: pig note
date: 2026-08-14
release_url: https://github.com/pgsty/pig/releases/tag/v1.9.0
---
""",
        )
        write(
            site / "content/blog/releases/mcli.md",
            """---
title: mcli note
date: 2026-08-13
---
""",
        )
        result = run(hugo, site)
        output = result.stdout + result.stderr
        if result.returncode != 0:
            errors.append(f"removed-keys fixture failed: {output}")
            return errors
        for key in ("release_products", "release_group_by_product"):
            require(
                f"{key} was removed with the release map" in output,
                f"naming {key} did not warn about its removal",
                errors,
            )
        require(
            run(hugo, site, panic_on_warning=True).returncode != 0,
            "removed list keys survived --panicOnWarning",
            errors,
        )
        parser = ReleaseIndexParser()
        parser.feed((site / "public/blog/releases/index.html").read_text(encoding="utf-8"))
        require(
            [(row["href"], row["name"]) for row in parser.rows]
            == [
                ("/blog/releases/pig/", "pig v1.9.0"),
                ("/blog/releases/mcli/", "mcli note"),
            ],
            "the removed keys changed what the index lists, or the mixed naming broke",
            errors,
        )
    return errors


INVALID_CASES = (
    (
        "release-url-bad-host",
        "release_url: https://gitlab.com/pgsty/oink/releases/tag/v1.0.0",
        "{{< release-card >}}",
        "release_url must match",
    ),
    ("release-url-scalar", "release_url: true", "{{< release-card >}}", "must be a GitHub release URL string"),
    # The 0.5 map and its string shorthand are gone; both name the successor.
    ("release-legacy-map", "release:\n  version: 1.0.0\n  repo: pgsty/oink", "{{< release-card >}}", "was replaced by `release_url`"),
    ("release-legacy-shorthand", "release: https://github.com/pgsty/oink/releases/tag/v1.0.0", "{{< release-card >}}", "was replaced by `release_url`"),
    ("release-card-param", "release_url: https://github.com/pgsty/oink/releases/tag/v1.0.0", '{{< release-card version="1.0.0" >}}', "accepts no parameters"),
    ("asset-bad-line", "", '{{< release-assets base="/files" >}}\nnot-a-sum\n{{< /release-assets >}}', "line 2 must be"),
    ("asset-bad-length", "", '{{< release-assets base="/files" >}}\naaaa  file.zip\n{{< /release-assets >}}', "unsupported hex length 4"),
    ("asset-mixed", "", '{{< release-assets base="/files" >}}\n' + "a" * 32 + "  old.zip\n" + "b" * 64 + "  new.zip\n{{< /release-assets >}}", "mixes checksum algorithms"),
    ("asset-override", "", '{{< release-assets base="/files" algo="sha256" >}}\n' + "a" * 32 + "  old.zip\n{{< /release-assets >}}", "conflicts with algo"),
    ("asset-dual-source", "", '{{< release-assets base="/files" src="release/shared-checksums.txt" >}}\n' + "a" * 64 + "  file.zip\n{{< /release-assets >}}", "mutually exclusive"),
    ("asset-missing-source", "", "{{< release-assets >}}\n" + "a" * 64 + "  file.zip\n{{< /release-assets >}}", "requires release_url front matter or base"),
    ("asset-bad-src", "", '{{< release-assets base="/files" src="missing.txt" >}}{{< /release-assets >}}', "was not found"),
    ("asset-release-base", "release_url: https://github.com/pgsty/oink/releases/tag/v1.0.0", '{{< release-assets base="/files" >}}\n' + "a" * 64 + "  file.zip\n{{< /release-assets >}}", "base is only valid without release_url front matter"),
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
            require(expected in output, f"invalid case {name} did not report {expected!r}", errors)
            require("content/docs/invalid.md:" in output, f"invalid case {name} lost its source position", errors)
            require(run(hugo, site, panic_on_warning=True).returncode != 0,
                    f"invalid case {name} survived --panicOnWarning", errors)
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
        and '"target" "js/chunks/asset-list.js"' in scripts,
        "asset-list is not gated as its stable capability chunk",
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
            result = run(args.hugo, FIXTURE, public)
            if result.returncode != 0:
                print("release fixture failed to build:")
                print(result.stdout + result.stderr)
                return 1
            errors = check_example(public)
    else:
        errors = check_example(args.public)

    errors += (
        check_algorithms_and_rss(args.hugo)
        + check_releases_layout(args.hugo)
        + check_removed_list_keys(args.hugo)
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
