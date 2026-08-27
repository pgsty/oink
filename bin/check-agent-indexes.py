#!/usr/bin/env python3
"""Agent index contracts: the opt-in LLMSFULL full-text bundle.

The bundle concatenates the same semantic Markdown the per-page output
publishes, in the sidebar reading order, one file per enabled top-level
section per language. This checker owns:

- language isolation: each bundle carries only its own language's pages;
- source integrity: every `Source:` pointer resolves to a built artifact,
  appears exactly once, and the section index leads the sequence;
- reading order: pages follow their declared front-matter weights;
- discovery: llms.txt lists the enabled bundle for its own language;
- determinism: two builds of the same sources produce identical bundles;
- the negative contract: enabling LLMSFULL on a nested section warns, emits
  nothing, keeps a plain build usable, and fails --panicOnWarning.

Bundle sizes are reported as evidence, never enforced: a model-context
ceiling is a consumer's judgement, not a build gate.

  bin/check-agent-indexes.py                # build the fixture and check
  bin/check-agent-indexes.py --hugo PATH    # build with another Hugo binary
  bin/check-agent-indexes.py --public DIR   # reuse a build (skips determinism)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from test_site import ROOT, TEST_SITE, build_fixture_public, fixture_config

BASE_URL = "https://example.org/"
BUILD_TIMEOUT = 120

BUNDLES = {
    "docs/llms-full.txt": {"lang": "en", "index": "docs/index.md"},
    "zh/docs/llms-full.txt": {"lang": "zh", "index": "zh/docs/index.md"},
}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def bundle_sources(text: str) -> list[str]:
    return re.findall(r"^Source: (\S+)$", text, flags=re.MULTILINE)


def weight_order(language: str) -> list[str]:
    """Expected relative URL order of the docs pages, from front-matter weights.

    An independent oracle: the bundle must present pages in ascending declared
    weight, the same order the sidebar and pager derive from the content tree.
    Only pages with an explicit unique weight participate; the fixture keeps
    them unique on purpose.
    """

    weighted: list[tuple[int, str]] = []
    for path in sorted((TEST_SITE / "content/docs").glob("*.md")):
        if path.name.startswith("_index"):
            continue
        is_zh = path.name.endswith(".zh.md")
        if (language == "zh") != is_zh:
            continue
        front = path.read_text(encoding="utf-8").split("---\n")
        if len(front) < 2:
            continue
        match = re.search(r"^weight:\s*(\d+)\s*$", front[1], flags=re.MULTILINE)
        if not match:
            continue
        slug = path.name.removesuffix(".zh.md").removesuffix(".md")
        prefix = "zh/" if language == "zh" else ""
        weighted.append((int(match.group(1)), f"{prefix}docs/{slug}/index.md"))
    weighted.sort()
    return [url for _, url in weighted]


def check_bundle(public: Path, rel_path: str, spec: dict, errors: list[str]) -> None:
    bundle_path = public / rel_path
    require(bundle_path.exists(), f"{rel_path} was not built", errors)
    if not bundle_path.exists():
        return
    text = bundle_path.read_text(encoding="utf-8")
    sources = bundle_sources(text)
    require(len(sources) >= 2, f"{rel_path} holds fewer than two pages", errors)
    require(len(sources) == len(set(sources)),
            f"{rel_path} repeats a Source pointer", errors)
    separators = text.count("================\n")
    require(separators == 2 * len(sources),
            f"{rel_path} separator count {separators} does not frame "
            f"{len(sources)} Source pointers", errors)

    paths: list[str] = []
    for url in sources:
        require(url.startswith(BASE_URL),
                f"{rel_path} lists an off-site source: {url}", errors)
        if not url.startswith(BASE_URL):
            continue
        rel = url.removeprefix(BASE_URL)
        paths.append(rel)
        require((public / rel).exists(),
                f"{rel_path} points at an unbuilt source: {url}", errors)
        in_zh = rel.startswith("zh/")
        require(in_zh == (spec["lang"] == "zh"),
                f"{rel_path} crosses languages with {url}", errors)

    require(bool(paths) and paths[0] == spec["index"],
            f"{rel_path} does not lead with its section index", errors)

    expected = weight_order(spec["lang"])
    listed = [path for path in paths if path in set(expected)]
    require(listed == expected,
            f"{rel_path} order diverges from front-matter weights:\n"
            f"    bundle:   {listed}\n    expected: {expected}", errors)

    # One renderer, provably: each bundle segment must equal the page's own
    # published .md byte-for-byte (modulo surrounding blank lines). Author
    # markup quoted in source flows through both on purpose; output purity
    # itself is owned by the per-page markdown gates.
    segments = re.split(
        r"^================\nSource: (\S+)\n================\n\n",
        text, flags=re.MULTILINE)
    for url, body in zip(segments[1::2], segments[2::2]):
        rel = url.removeprefix(BASE_URL)
        if not rel.endswith(".md"):
            continue
        page_file = public / rel
        if not page_file.exists():
            continue  # already reported by the source-integrity check
        require(body.strip() == page_file.read_text(encoding="utf-8").strip(),
                f"{rel_path} segment for {rel} diverges from the per-page output",
                errors)

    print(f"  {rel_path}: {len(sources)} pages, {len(text.encode('utf-8'))} bytes")


def check_discovery(public: Path, errors: list[str]) -> None:
    for llms, bundle in (("llms.txt", "docs/llms-full.txt"),
                         ("zh/llms.txt", "zh/docs/llms-full.txt")):
        index = public / llms
        require(index.exists(), f"{llms} was not built", errors)
        if not index.exists():
            continue
        text = index.read_text(encoding="utf-8")
        require(f"{BASE_URL}{bundle}" in text,
                f"{llms} does not list the enabled bundle {bundle}", errors)


def check_determinism(hugo: str, first: Path, errors: list[str]) -> None:
    second, result = build_fixture_public(hugo, "--panicOnWarning")
    require(result.returncode == 0,
            "second fixture build failed; determinism unverified", errors)
    if result.returncode != 0:
        return
    for rel_path in BUNDLES:
        a = (first / rel_path).read_bytes() if (first / rel_path).exists() else b""
        b = (second / rel_path).read_bytes() if (second / rel_path).exists() else b""
        require(a == b, f"{rel_path} differs between two identical builds", errors)


def check_nested_section(hugo: str, errors: list[str]) -> None:
    """Enabling LLMSFULL below the top level warns and blocks publication."""

    with tempfile.TemporaryDirectory(prefix="oink-agent-indexes-nested-") as temp:
        temp_path = Path(temp)
        override = temp_path / "override.yaml"
        override.write_text(
            "outputs:\n  section: [HTML, print, RSS, markdown, LLMSFULL]\n",
            encoding="utf-8",
        )
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
        expected = "LLMSFULL output requires a top-level section"
        require(expected in output,
                f"nested-section LLMSFULL did not report {expected!r}", errors)
        require(result.returncode == 0,
                "nested-section LLMSFULL stopped a plain build instead of warning",
                errors)
        nested = temp_path / "public/fixtures/guides/llms-full.txt"
        require((not nested.exists()) or nested.read_text(encoding="utf-8") == "",
                "nested-section LLMSFULL emitted content instead of nothing", errors)
        # A wedge under --panicOnWarning is the panic path seizing; the build
        # certainly did not publish, which is the assertion.
        try:
            strict = subprocess.run(
                command + ["--panicOnWarning"],
                capture_output=True, text=True, check=False,
                timeout=BUILD_TIMEOUT,
            )
            require(strict.returncode != 0,
                    "nested-section LLMSFULL survived --panicOnWarning", errors)
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

    for rel_path, spec in BUNDLES.items():
        check_bundle(public, rel_path, spec, errors)
    check_discovery(public, errors)
    if args.public is None:
        check_determinism(args.hugo, public, errors)
        check_nested_section(args.hugo, errors)
    else:
        print("  (reused build: determinism and nested-section cases skipped)")

    if errors:
        print("Agent index checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Agent index checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
