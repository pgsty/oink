#!/usr/bin/env python3
"""Four-state output goldens for the private fixture overlay.

The pages listed in tests/goldens/manifest.json are built by mounting
tests/site/ over exampleSite, normalised
(fingerprint hashes, SRI attributes, Hugo version, absolute build paths) and
compared line-for-line (indentation-insensitive, blank lines dropped) against tests/goldens/<name>. One golden per output state
per surface: html, print, markdown, rss, llms.

  bin/check-goldens.py                # compare (default)
  bin/check-goldens.py --update       # rewrite the goldens from the current build
  bin/check-goldens.py --hugo PATH    # build with another Hugo binary
  bin/check-goldens.py --public DIR   # reuse an existing private-fixture build

Goldens are shared between the CI Hugo versions; a version-specific difference
must be normalised here (never by keeping two copies silently). Update goldens
in the same commit as the behaviour change and say why in the message.
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

from test_site import build_fixture_public

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
GOLDENS = ROOT / "tests/goldens"
MANIFEST = GOLDENS / "manifest.json"

NORMALISERS = [
    (re.compile(r"\.min\.[0-9a-f]{64}\."), ".min.<hash>."),
    (re.compile(r"page-[0-9a-f]{32}\.min\.<hash>\.js"), "page-<bundle>.min.<hash>.js"),
    (re.compile(r"page-[0-9a-f]{32}\.js"), "page-<bundle>.js"),
    (re.compile(r'integrity="sha256-[A-Za-z0-9+/=&#;]+"'), 'integrity="<sri>"'),
    (re.compile(r"[?&]v=[0-9a-f]{6,}"), "?v=<hash>"),
    (re.compile(r"_hu_[0-9a-f]+\."), "_hu_<hash>."),  # processed image cache keys differ per Hugo version
    (re.compile(r"offline-search-index\.([a-z-]+)\.[0-9a-f]{32}\.json"), r"offline-search-index.\1.<hash>.json"),  # index hash tracks all fixture content
    (re.compile(r'content="Hugo \d+\.\d+\.\d+[^"]*"'), 'content="Hugo <version>"'),
    (re.compile(r"Hugo v?\d+\.\d+\.\d+"), "Hugo <version>"),
    (re.compile(r"/tmp/[A-Za-z0-9._-]+/|/private/tmp/[A-Za-z0-9._/-]+?/exampleSite/"), "<tmp>/"),
]


def normalise(text: str) -> str:
    for pattern, replacement in NORMALISERS:
        text = pattern.sub(replacement, text)
    # Hugo's embedded templates and Goldmark indent output differently between
    # 0.160.1 and 0.164.0 (tabs vs spaces, blank lines); compare structure, not
    # indentation: strip leading whitespace per line and drop empty lines.
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line) + "\n"


def build(hugo: str) -> Path:
    dest, result = build_fixture_public(
        hugo,
        "--printPathWarnings",
        "--panicOnWarning",
        "--quiet",
    )
    if result.returncode != 0:
        print(result.stdout + result.stderr, file=sys.stderr)
        raise SystemExit("exampleSite build failed")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--public", type=Path)
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--diff-lines", type=int, default=40)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    public = args.public or build(args.hugo)
    errors: list[str] = []
    for golden_name, output_path in sorted(manifest["pages"].items()):
        source = public / output_path
        if not source.exists():
            errors.append(f"{output_path} was not built")
            continue
        actual = normalise(source.read_text(encoding="utf-8", errors="replace"))
        golden = GOLDENS / golden_name
        if args.update:
            golden.parent.mkdir(parents=True, exist_ok=True)
            golden.write_text(actual, encoding="utf-8")
            continue
        if not golden.exists():
            errors.append(f"{golden_name}: golden missing (run --update)")
            continue
        expected = golden.read_text(encoding="utf-8")
        if expected != actual:
            diff = list(difflib.unified_diff(expected.splitlines(), actual.splitlines(), f"golden/{golden_name}", output_path, lineterm="", n=2))
            errors.append(f"{golden_name} differs from {output_path}:\n    " + "\n    ".join(diff[: args.diff_lines]))
    if args.update:
        print(f"updated {len(manifest['pages'])} goldens")
        return 0
    if errors:
        print("Golden checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print(f"Golden checks passed ({len(manifest['pages'])} surfaces)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
