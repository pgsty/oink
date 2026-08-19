#!/usr/bin/env python3
"""Validate download data normalization and output isolation."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import tempfile

from test_site import fixture_config_args


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
    hugo: str, source: Path, destination: Path | None = None,
    panic_on_warning: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [hugo, "--source", str(source), "--logLevel", "warn"]
    if source == EXAMPLE:
        command.extend(fixture_config_args())
    if destination is not None:
        command.extend(["--destination", str(destination)])
    if panic_on_warning:
        command.append("--panicOnWarning")
    return subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, check=False
    )


def create_site(root: Path, data: str, body: str = '{{< download "demo" >}}') -> None:
    (root / "themes").mkdir(parents=True)
    (root / "themes/oink").symlink_to(ROOT, target_is_directory=True)
    write(
        root / "hugo.yaml",
        """baseURL: https://example.org/
title: Download fixture
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
""",
    )
    write(
        root / "content/docs/_index.md",
        "---\ntitle: Docs\ntype: docs\ncascade:\n  type: docs\n---\n",
    )
    write(
        root / "content/docs/page.md",
        f"---\ntitle: Download\ndate: 2026-08-14\n---\n\n{body}\n",
    )
    if data:
        write(root / "data/download/demo.yaml", data)


def bundle(source: str) -> str:
    match = MAIN_SCRIPT.search(source)
    return match.group("src") if match else ""


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def visible_text(source: str) -> str:
    parser = TextParser()
    parser.feed(source)
    return " ".join(" ".join(parser.parts).split())


def check_example(public: Path) -> list[str]:
    errors: list[str] = []
    demo_path = public / "fixtures/download-demo/index.html"
    pending_path = public / "fixtures/download-pending/index.html"
    for path in (demo_path, pending_path):
        require(path.exists(), f"download fixture is missing: {path.name}", errors)
    if not demo_path.exists() or not pending_path.exists():
        return errors

    demo = demo_path.read_text(encoding="utf-8")
    pending = pending_path.read_text(encoding="utf-8")
    demo_text = visible_text(demo)
    pending_text = visible_text(pending)
    for marker in (
        'aria-label="Download channels"',
        'href="#download-demo-script"',
        'href="#download-demo-source"',
        'href="#download-demo-assets"',
        'data-td-download-kind="rolling"',
        'data-td-download-kind="pinned"',
        'class="chroma"',
        "data-td-code-copy",
        "data-td-asset-copy-all",
        "https://github.com/pgsty/oink/archive/refs/tags/v2.4.1.tar.gz",
        "https://github.com/pgsty/oink/releases/download/v2.4.1/demo-2.4.1-linux-amd64.tar.gz",
    ):
        require(marker in demo, f"published download fixture lost {marker}", errors)
    for marker in (
        "curl -fsSL https://repo.example.org/demo | bash",
        "git clone --branch v2.4.1 https://github.com/pgsty/oink.git",
    ):
        require(marker in demo_text, f"published download fixture lost visible command {marker}", errors)
    require("${" not in demo, "published download leaked an interpolation token", errors)

    for marker in (
        "Pending release",
        'aria-disabled="true"',
        "oink-3.0.0-rc.1.tar.gz",
    ):
        require(marker in pending, f"unpublished download fixture lost {marker}", errors)
    require(
        "curl -fsSL https://repo.example.org/oink/install | bash" in pending_text,
        "unpublished download fixture lost its rolling command",
        errors,
    )
    for marker in (
        "releases/tag/v3.0.0-rc.1",
        "releases/download/v3.0.0-rc.1",
        "data-td-asset-copy",
        "oink-${version}",
    ):
        require(marker not in pending, f"unpublished pinned channel leaked {marker}", errors)
    require(
        'href="https://repo.example.org/oink/"' in pending,
        "unpublished state incorrectly disabled its rolling channel",
        errors,
    )
    require(
        pending.count("data-td-code-copy") == 1,
        "unpublished pinned code still requested a copy control",
        errors,
    )

    demo_bundle = bundle(demo)
    pending_bundle = bundle(pending)
    plain = (public / "blog/release/pig-1.9.0/index.html").read_text(encoding="utf-8")
    plain_bundle = bundle(plain)
    require(demo_bundle and pending_bundle and plain_bundle, "download fixture lost a bundle", errors)
    require(demo_bundle != plain_bundle, "download code/assets did not alter runtime bundle", errors)
    require(pending_bundle != plain_bundle, "rolling download code did not alter runtime bundle", errors)
    if demo_bundle:
        source = (public / demo_bundle.lstrip("/")).read_text(encoding="utf-8")
        require("OinkAssetList" in source, "published download did not bundle asset runtime", errors)
        require("OINK code block: unable to copy code:" in source, "published download did not bundle code runtime", errors)
    if pending_bundle:
        source = (public / pending_bundle.lstrip("/")).read_text(encoding="utf-8")
        require("OinkAssetList" not in source, "unpublished download bundled disabled asset runtime", errors)
        require("OINK code block: unable to copy code:" in source, "unpublished rolling channel lost code runtime", errors)

    demo_md = (public / "fixtures/download-demo/index.md").read_text(encoding="utf-8")
    pending_md = (public / "fixtures/download-pending/index.md").read_text(encoding="utf-8")
    for marker in (
        "## Install script",
        "```bash\ncurl -fsSL https://repo.example.org/demo | bash\n```",
        "git clone --branch v2.4.1",
        "| File | Checksum |",
        "c" * 64,
    ):
        require(marker in demo_md, f"download Markdown lost {marker}", errors)
    for marker in ("td-download", "td-code", "data-", "<table", "<button"):
        require(marker not in demo_md, f"download Markdown contains {marker}", errors)
    require("**Pending release**" in pending_md, "unpublished Markdown lost pending state", errors)
    require("releases/tag/v3.0.0-rc.1" not in pending_md, "unpublished Markdown leaked pinned URL", errors)
    require("releases/download/v3.0.0-rc.1" not in pending_md, "unpublished Markdown leaked asset URL", errors)
    require("oink\\-3\\.0\\.0\\-rc\\.1\\.tar\\.gz" in pending_md, "unpublished Markdown lost asset identity", errors)

    for name, source_marker in (
        ("download-demo", "git clone --branch v2.4.1"),
        ("download-pending", "curl -fsSL https://repo.example.org/oink/install"),
    ):
        path = public / f"_print/fixtures/{name}/index.html"
        require(path.exists(), f"download print fixture is missing: {name}", errors)
        if path.exists():
            source = path.read_text(encoding="utf-8")
            require(source_marker in visible_text(source), f"download print lost {source_marker}", errors)
            for marker in ("td-download__chip", "data-td-code-copy", "data-td-asset-copy"):
                require(marker not in source, f"download print contains {marker}", errors)
    return errors


def check_site_version_fallback(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-download-version-") as temp:
        site = Path(temp)
        create_site(
            site,
            """repo: pgsty/oink
channels:
  - id: source
    kind: pinned
    title: Source
    url: https://example.org/${tag}/source.zip
""",
        )
        config = (site / "hugo.yaml").read_text(encoding="utf-8")
        write(site / "hugo.yaml", config.replace("  offline_search", "  version: 4.2.0\n  offline_search"))
        result = run(hugo, site)
        if result.returncode != 0:
            errors.append(f"site version fallback fixture failed: {result.stdout}{result.stderr}")
        else:
            source = (site / "public/docs/page/index.html").read_text(encoding="utf-8")
            require('href="https://example.org/v4.2.0/source.zip"' in source, "site params.version fallback failed", errors)
    return errors


def check_rss(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-components-download-rss-") as temp:
        site = Path(temp)
        create_site(
            site,
            """version: 1.0.0
channels:
  - id: script
    kind: rolling
    title: Script
    steps:
      - code: echo rolling
        lang: bash
""",
        )
        config = (site / "hugo.yaml").read_text(encoding="utf-8")
        write(
            site / "hugo.yaml",
            config.replace("disableKinds: [RSS,", "disableKinds: [").replace("page: [HTML]", "page: [RSS]"),
        )
        write(
            site / "content/docs/page.md",
            "---\ntitle: Download\ndate: 2026-08-14\noutputs: [RSS]\n---\n\nBefore.\n\n{{< download \"demo\" >}}\n\nAfter.\n",
        )
        write(
            site / "layouts/docs/single.rss.xml",
            '{{- .Store.Set "tdOutputFormat" "rss" -}}<fixture>{{ .RenderShortcodes }}</fixture>\n',
        )
        result = run(hugo, site)
        if result.returncode != 0:
            errors.append(f"download RSS fixture failed: {result.stdout}{result.stderr}")
        else:
            outputs = list((site / "public/docs").rglob("*.xml"))
            require(len(outputs) == 1, "download RSS fixture did not emit one output", errors)
            if outputs:
                source = outputs[0].read_text(encoding="utf-8")
                require("Before." in source and "After." in source, "RSS lost surrounding content", errors)
                for marker in ("td-download", "Download channels", "echo rolling", "data-download"):
                    require(marker not in source, f"RSS did not strip download component: {marker}", errors)
    return errors


BASE = """version: 1.0.0
repo: pgsty/oink
channels:
  - id: script
    kind: rolling
    title: Script
    steps:
      - code: echo safe
        lang: bash
"""

INVALID_CASES = (
    ("missing-key", "", '{{< download "missing" >}}', "was not found"),
    ("named", BASE, '{{< download key="demo" >}}', "requires exactly one positional data key"),
    ("missing-arg", BASE, "{{< download >}}", "requires exactly one positional data key"),
    ("extra-arg", BASE, '{{< download "demo" "extra" >}}', "requires exactly one positional data key"),
    ("bad-key", BASE, '{{< download "../demo" >}}', "download key must match"),
    ("missing-version", "channels:\n  - id: x\n    kind: rolling\n    title: X", '{{< download "demo" >}}', "download version is required"),
    ("version-type", "version: 1\nchannels:\n  - id: x\n    kind: rolling\n    title: X", '{{< download "demo" >}}', "download version must be a string"),
    ("bad-kind", BASE.replace("kind: rolling", "kind: stable"), '{{< download "demo" >}}', "kind must be rolling or pinned"),
    ("rolling-code-version", BASE.replace("echo safe", "echo ${version}"), '{{< download "demo" >}}', "rolling download channel step code must not interpolate"),
    ("rolling-url-version", BASE.replace("    steps:", "    url: https://example.org/${tag}/\n    steps:"), '{{< download "demo" >}}', "rolling download channel url must not interpolate"),
    ("unknown-var", BASE.replace("kind: rolling", "kind: pinned").replace("echo safe", "echo ${branch}"), '{{< download "demo" >}}', "unknown interpolation variable"),
    ("malformed-var", BASE.replace("kind: rolling", "kind: pinned").replace("echo safe", "echo ${version"), '{{< download "demo" >}}', "malformed interpolation syntax"),
    ("title-interpolation", BASE.replace("title: Script", "title: Script ${version}"), '{{< download "demo" >}}', "title must not interpolate"),
    ("duplicate-id", BASE + "\n  - id: script\n    kind: rolling\n    title: Again\n", '{{< download "demo" >}}', "duplicate id"),
    ("bad-id", BASE.replace("id: script", "id: Bad_ID"), '{{< download "demo" >}}', "id must match"),
    ("channels-scalar", "version: 1.0.0\nchannels: script", '{{< download "demo" >}}', "channels must be an array"),
    ("checksums-rolling", BASE.replace("    steps:", "    checksums: |\n      " + "a" * 64 + "  demo.zip\n    steps:"), '{{< download "demo" >}}', "checksums are valid only for a pinned channel"),
    ("pinned-repo", BASE.replace("repo: pgsty/oink\n", "").replace("kind: rolling", "kind: pinned").replace("    steps:", "    url: https://example.org/file\n    steps:"), '{{< download "demo" >}}', "pinned links/assets require download repo"),
    ("published-type", BASE.replace("channels:", "published: \"false\"\nchannels:"), '{{< download "demo" >}}', "published must be a boolean"),
    ("bad-url", BASE.replace("    steps:", "    url: javascript:alert(1)\n    steps:"), '{{< download "demo" >}}', "url must use http or https"),
    ("unknown-field", BASE.replace("channels:", "future: true\nchannels:"), '{{< download "demo" >}}', "unsupported field"),
    ("duplicate-component", BASE, '{{< download "demo" >}}\n{{< download "demo" >}}', "duplicate data key"),
)


def check_invalid(hugo: str) -> list[str]:
    errors: list[str] = []
    for name, data, body, expected in INVALID_CASES:
        with tempfile.TemporaryDirectory(prefix=f"oink-components-download-{name}-") as temp:
            site = Path(temp)
            create_site(site, data, body)
            result = run(hugo, site)
            output = result.stdout + result.stderr
            # A malformed record warns and resolves to an empty block; the page
            # still builds. --panicOnWarning is what keeps it fatal on publish.
            require(result.returncode == 0,
                    f"invalid download case {name} stopped the build instead of warning:\n{output[-400:]}", errors)
            require(expected in output, f"invalid download case {name} did not report {expected!r}", errors)
            require("content/docs/page.md:" in output, f"invalid download case {name} lost its source position", errors)
            strict = run(hugo, site, panic_on_warning=True)
            require(strict.returncode != 0,
                    f"invalid download case {name} survived --panicOnWarning", errors)
    return errors


def check_sources() -> list[str]:
    errors: list[str] = []
    resolver = (ROOT / "layouts/_partials/download/resolve.html").read_text(encoding="utf-8")
    renderer = (ROOT / "layouts/_partials/download/render.html").read_text(encoding="utf-8")
    styles = (ROOT / "assets/scss/td/_release.scss").read_text(encoding="utf-8")
    require('partial "code/normalize.html"' in (ROOT / "layouts/_partials/download/code.html").read_text(), "download code does not reuse enhanced code normalization", errors)
    require('partial "release/assets-parse.html"' in renderer, "download assets do not reuse release parser", errors)
    require("rolling download channel" in (ROOT / "layouts/_partials/download/interpolate.html").read_text(), "rolling interpolation guard is missing", errors)
    require('Store.Set "hasAssetList" true' in renderer, "download assets never request their runtime", errors)
    require("<nav" in renderer and "td-download__channels" in renderer, "download chip navigation is missing", errors)
    require("@media print" in styles and "@media (forced-colors: active)" in styles, "download styles lack accessibility media", errors)
    require("localized.html" in resolver, "download localized fallback helper is unused", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--public", type=Path)
    args = parser.parse_args()

    if args.public is None:
        with tempfile.TemporaryDirectory(prefix="oink-components-download-example-") as temp:
            public = Path(temp) / "public"
            result = run(args.hugo, EXAMPLE, public)
            if result.returncode != 0:
                print("download fixture failed to build:")
                print(result.stdout + result.stderr)
                return 1
            errors = check_example(public)
    else:
        errors = check_example(args.public)
    errors += check_site_version_fallback(args.hugo) + check_rss(args.hugo) + check_invalid(args.hugo) + check_sources()
    if errors:
        print("download checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("download checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
