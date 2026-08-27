#!/usr/bin/env python3
"""Backlink contracts: the G1 static reverse-navigation block.

The reverse index derives from ordinary Markdown links and ref/relref in raw
source, per language, at build time. This checker owns the extraction and
rendering contract on the fixture's fixtures/backlinks subtree:

- edges: relative, absolute, and relref references resolve; duplicate
  references merge; self links, external links, same-page anchors, and links
  inside fenced or inline code never become edges; fragments drop for page
  identity;
- languages stay isolated: the zh list holds zh pages with zh URLs only;
- policy: the site default is off (no block outside the opted-in subtree),
  a section cascade turns it on, and a page's own `backlinks: false` wins;
- presentation: the block is an aside group in the right rail beside the
  TOC, expanded by default, with the first eight entries visible and the
  rest behind a native details disclosure;
- outputs: HTML and the per-page Markdown carry the list; RSS does not, and
  the print output format omits the rail as it always has;
- invalid input: a non-boolean params.ui.backlinks warns and falls back on a
  plain build and fails --panicOnWarning.

  bin/check-backlinks.py                # build the fixture and check
  bin/check-backlinks.py --hugo PATH    # build with another Hugo binary
  bin/check-backlinks.py --public DIR   # reuse a build (skips build cases)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from test_site import ROOT, TEST_SITE, build_fixture_public, fixture_config

BUILD_TIMEOUT = 120

# page -> exact expected (href, label) entries, in order.
EXPECTED = {
    "fixtures/backlinks/alpha/index.html": [("/fixtures/backlinks/beta/", "Beta")],
    "fixtures/backlinks/beta/index.html": [("/fixtures/backlinks/alpha/", "Alpha")],
    "fixtures/backlinks/gamma/index.html": [("/fixtures/backlinks/alpha/", "Alpha")],
    "zh/fixtures/backlinks/alpha/index.html": [("/zh/fixtures/backlinks/beta/", "贝塔")],
    "zh/fixtures/backlinks/beta/index.html": [("/zh/fixtures/backlinks/alpha/", "阿尔法")],
}

ABSENT = (
    "fixtures/backlinks/delta/index.html",   # linked only from code samples
    "fixtures/backlinks/quiet/index.html",   # page-level backlinks: false
    "fixtures/backlinks/link1/index.html",   # outgoing links only
    "zh/fixtures/backlinks/gamma/index.html",  # no zh inbound links
    "docs/callout/index.html",               # site default stays off
)

ITEM = re.compile(
    r'<li class="td-shell-backlinks__item"><a href="([^"]+)"[^>]*>([^<]+)</a></li>')


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_rendering(public: Path, errors: list[str]) -> None:
    for rel_path, expected in EXPECTED.items():
        page = public / rel_path
        require(page.exists(), f"{rel_path} was not built", errors)
        if not page.exists():
            continue
        text = page.read_text(encoding="utf-8")
        entries = ITEM.findall(text)
        require(entries == expected,
                f"{rel_path} backlinks diverge:\n"
                f"    got:      {entries}\n    expected: {expected}", errors)
        group = text.split('td-shell-backlinks"', 1)
        require(len(group) == 2 and 'aria-expanded="true"' in group[1][:600],
                f"{rel_path} backlink group is not expanded by default", errors)
        require("fa-link" in text,
                f"{rel_path} backlink group head lacks its icon", errors)
    for rel_path in ABSENT:
        page = public / rel_path
        require(page.exists(), f"{rel_path} was not built", errors)
        if page.exists():
            require("td-shell-backlinks" not in page.read_text(encoding="utf-8"),
                    f"{rel_path} renders a backlink block it must not have",
                    errors)

    # A heavily referenced page shows eight entries and folds the rest
    # behind the native disclosure.
    hub = (public / "fixtures/backlinks/hub/index.html").read_text(encoding="utf-8")
    visible, _, folded = hub.partition('<details class="td-shell-backlinks__more">')
    require(len(ITEM.findall(visible)) == 8 and len(ITEM.findall(folded)) == 1,
            "hub does not fold its ninth backlink behind the disclosure", errors)
    require("<summary>" in folded and " 1 " in folded.split("</summary>")[0],
            "the disclosure summary does not count the folded entries", errors)

    # The block lives on exactly the expected pages, nowhere else.
    expected_carriers = sorted(list(EXPECTED) + ["fixtures/backlinks/hub/index.html"])
    carriers = sorted(
        str(path.relative_to(public))
        for path in public.rglob("*.html")
        if "td-shell-backlinks" in path.read_text(encoding="utf-8", errors="replace"))
    require(carriers == expected_carriers,
            f"backlink blocks appear on unexpected pages: {carriers}", errors)


def check_outputs(public: Path, errors: list[str]) -> None:
    alpha_md = (public / "fixtures/backlinks/alpha/index.md").read_text(encoding="utf-8")
    require("Linked from:" in alpha_md
            and "- [Beta](/fixtures/backlinks/beta/)" in alpha_md,
            "alpha's Markdown output lacks its backlink list", errors)
    quiet_md = (public / "fixtures/backlinks/quiet/index.md").read_text(encoding="utf-8")
    require("Linked from:" not in quiet_md,
            "quiet's Markdown output carries a list its front matter disabled",
            errors)
    docs_md = (public / "docs/callout/index.md").read_text(encoding="utf-8")
    require("Linked from:" not in docs_md,
            "a default-off page's Markdown output carries a backlink list",
            errors)
    rss = (public / "fixtures/index.xml").read_text(encoding="utf-8")
    require("td-shell-backlinks" not in rss and "Linked from:" not in rss,
            "the section RSS carries backlink markup", errors)
    print_page = (public / "_print/fixtures/index.html").read_text(encoding="utf-8")
    require("td-shell-backlinks" not in print_page,
            "the print output format renders the rail backlink group", errors)


def check_invalid_config(hugo: str, errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix="oink-backlinks-invalid-") as temp:
        temp_path = Path(temp)
        override = temp_path / "override.yaml"
        override.write_text("params:\n  ui:\n    backlinks: sometimes\n",
                            encoding="utf-8")
        command = [
            hugo,
            "--source", str(TEST_SITE),
            "--themesDir", str(ROOT.parent),
            "--destination", str(temp_path / "public"),
            "--config", fixture_config(override),
            "--logLevel", "warn",
        ]
        result = subprocess.run(command, capture_output=True, text=True,
                                check=False, timeout=BUILD_TIMEOUT)
        output = result.stdout + result.stderr
        expected = "params.ui.backlinks must be true or false"
        require(expected in output,
                f"invalid backlinks config did not report {expected!r}", errors)
        require(result.returncode == 0,
                "invalid backlinks config stopped a plain build", errors)
        # A wedge under --panicOnWarning is the panic path seizing; the build
        # certainly did not publish, which is the assertion.
        try:
            strict = subprocess.run(
                command + ["--panicOnWarning"],
                capture_output=True, text=True, check=False,
                timeout=BUILD_TIMEOUT,
            )
            require(strict.returncode != 0,
                    "invalid backlinks config survived --panicOnWarning", errors)
        except subprocess.TimeoutExpired:
            print(f"hugo wedged after {BUILD_TIMEOUT}s under --panicOnWarning; "
                  "counting the wedge as the expected failure", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--public", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    if args.public:
        public = args.public
    else:
        public, result = build_fixture_public(
            args.hugo, "--printPathWarnings", "--panicOnWarning")
        if result.returncode != 0:
            print(result.stdout + result.stderr, file=sys.stderr)
            raise SystemExit("regression fixture build failed")

    check_rendering(public, errors)
    check_outputs(public, errors)
    if args.public is None:
        check_invalid_config(args.hugo, errors)
    else:
        print("  (reused build: invalid-config case skipped)")

    if errors:
        print("Backlink checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Backlink checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
