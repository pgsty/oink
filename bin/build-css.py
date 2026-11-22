#!/usr/bin/env python3
"""Compile the theme's SCSS into the CSS bundles that ship in assets/oink/.

Site builds read those bundles and never call a Sass compiler. Only theme
maintainers run this script, after editing anything under assets/scss/ or the
vendored SCSS it imports. Every assets/scss/<name>.scss whose name has no
leading underscore is an entry and becomes assets/oink/<name>.css.

    python3 bin/build-css.py            # rewrite stale bundles
    python3 bin/build-css.py --check    # fail when a shipped bundle is stale
    python3 bin/build-css.py --watch    # rebuild while editing SCSS

The release compiler is LibSass, which only Hugo Extended up to 0.169 contains.
Where the default `hugo` is newer, keep that release on PATH as `hugo-0.169.0`
or name it with --hugo. Site builds are unaffected: they use any Hugo.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from test_site import ROOT, run_hugo_process


SOURCE = ROOT / "assets" / "scss"
OUTPUT = ROOT / "assets" / "oink"
# SCSS outside assets/scss/ that the entries import.
VENDORED = ("bootstrap/scss", "inter", "ibm-plex-sans")
# Hugo executables to try for LibSass, in order, when --hugo is not given.
LIBSASS_HUGO = ("hugo", "hugo-0.169.0")

LAYOUT = """{{- range $name := site.Params.entries -}}
  {{- $options := dict "transpiler" "libsass" "outputStyle" "expanded" -}}
  {{- with resources.Get (printf "scss/%s.scss" $name) -}}
    {{- (. | css.Sass $options).Publish -}}
  {{- end -}}
{{- end -}}
"""


def has_libsass(hugo: str) -> bool:
    """LibSass ships only in the Extended edition, which ended with Hugo 0.169."""

    result = subprocess.run([hugo, "version"], text=True, capture_output=True)
    return "+extended" in result.stdout


def find_compiler(requested: str | None) -> str:
    """Return the Hugo executable that will run LibSass."""

    names = (requested,) if requested else LIBSASS_HUGO
    found = [path for path in map(shutil.which, names) if path]
    if not found:
        raise SystemExit(f"Hugo executable not found: {', '.join(names)}")
    for path in found:
        if has_libsass(path):
            return path
    raise SystemExit(
        f"No LibSass in {', '.join(found)}: Hugo 0.170 removed it. Keep Hugo Extended 0.169.0 "
        "on PATH as hugo-0.169.0, or pass --hugo <path to it>.")


def entries() -> list[str]:
    return sorted(path.stem for path in SOURCE.glob("*.scss")
                  if not path.name.startswith("_"))


def compile_bundles(hugo: str) -> dict[str, bytes]:
    """Return {entry name: compiled CSS} from a fresh, isolated Hugo build."""

    names = entries()
    with tempfile.TemporaryDirectory(prefix="oink-css-") as directory:
        site = Path(directory)
        (site / "layouts").mkdir()
        (site / "layouts" / "home.html").write_text(LAYOUT, encoding="utf-8")
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\n"
            "disableKinds: [page, section, taxonomy, term, rss, sitemap, robotstxt, 404]\n"
            "module:\n"
            "  mounts:\n"
            f"    - source: {ROOT / 'assets'}\n"
            "      target: assets\n"
            "params:\n"
            f"  entries: [{', '.join(names)}]\n",
            encoding="utf-8",
        )
        env = os.environ.copy()
        # No inherited module wiring and no cached transform may stand in for
        # the compiler. LibSass is inside Hugo, so the build needs no PATH.
        env.update(GOWORK="off", HUGO_MODULE_WORKSPACE="off",
                   HUGO_RESOURCEDIR=str(site / "resources"))
        env.pop("HUGO_MODULE_REPLACEMENTS", None)
        env["PATH"] = str(site / "empty-path")
        command = [hugo, "--source", str(site), "--destination", str(site / "public"),
                   "--cacheDir", str(site / "cache"), "--ignoreCache", "--noBuildLock",
                   "--logLevel", "warn", "--environment", "production"]
        result = run_hugo_process(command, env=env, text=True, capture_output=True)
        output = result.stdout + result.stderr
        errors = [line for line in output.splitlines() if line.startswith("ERROR")]
        if result.returncode or errors:
            raise SystemExit(f"Sass build failed:\n{output}")
        bundles = {}
        for name in names:
            path = site / "public" / "scss" / f"{name}.css"
            if not path.is_file():
                raise SystemExit(f"Sass build produced no output for {name}.scss:\n{output}")
            bundles[name] = path.read_bytes()
        return bundles


def stale(bundles: dict[str, bytes]) -> list[str]:
    """Name every shipped bundle that differs from a fresh compile."""

    problems = []
    for name, content in bundles.items():
        path = OUTPUT / f"{name}.css"
        if not path.is_file():
            problems.append(f"{path.relative_to(ROOT)}: missing")
        elif path.read_bytes() != content:
            problems.append(f"{path.relative_to(ROOT)}: differs from assets/scss/{name}.scss")
    expected = {f"{name}.css" for name in bundles}
    if OUTPUT.is_dir():
        for path in sorted(OUTPUT.glob("*.css")):
            if path.name not in expected:
                problems.append(f"{path.relative_to(ROOT)}: no assets/scss/{path.stem}.scss entry")
    return problems


def write(bundles: dict[str, bytes]) -> list[str]:
    OUTPUT.mkdir(exist_ok=True)
    changed = []
    for name, content in bundles.items():
        path = OUTPUT / f"{name}.css"
        if not path.is_file() or path.read_bytes() != content:
            path.write_bytes(content)
            changed.append(path.name)
    return changed


def source_state() -> tuple[tuple[str, int], ...]:
    roots = [SOURCE, *(ROOT / "assets" / "third_party" / part for part in VENDORED)]
    return tuple(sorted((str(path), path.stat().st_mtime_ns)
                        for root in roots for path in root.rglob("*.scss")))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--hugo", help="Hugo that runs the compiler; default: hugo, then "
                                       "hugo-0.169.0, whichever has LibSass")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true",
                      help="compare shipped bundles with a fresh compile; write nothing")
    mode.add_argument("--watch", action="store_true",
                      help="rebuild whenever an SCSS source changes")
    args = parser.parse_args()
    hugo = find_compiler(args.hugo)

    if args.check:
        problems = stale(compile_bundles(hugo))
        if problems:
            raise SystemExit("Shipped CSS is stale; run python3 bin/build-css.py:\n  "
                             + "\n  ".join(problems))
        print(f"CSS bundles are current: {', '.join(entries())}")
        return

    seen = None
    while True:
        state = source_state() if args.watch else None
        if state != seen or not args.watch:
            try:
                changed = write(compile_bundles(hugo))
            except (SystemExit, subprocess.SubprocessError, RuntimeError) as error:
                if not args.watch:
                    raise
                print(error)
            else:
                print("updated " + ", ".join(changed) if changed else "CSS bundles are current")
            seen = state
        if not args.watch:
            return
        time.sleep(0.5)


if __name__ == "__main__":
    main()
