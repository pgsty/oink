#!/usr/bin/env python3
"""Verify that a site build uses the shipped CSS and never compiles Sass.

    python3 bin/check-scss.py                    # both halves
    python3 bin/check-scss.py --skip-freshness   # the site-build half only

The site-build half needs nothing but the Hugo under test. Only the freshness
half recompiles the bundles, so only it needs a Hugo that contains LibSass.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from test_site import ROOT, run_hugo_process


SASS_CALL = re.compile(r"\b(?:toCSS|css\.Sass|resources\.ToCSS)\b")
LEGACY_HOOKS = ("_variables_project", "_variables_project_after_bs", "_styles_project")
PROJECT_CSS = ".oink-project-probe { width: 42px; }\n"
# css/project/*.css follows css/project.css in path order.
PROJECT = {
    "assets/css/project.css": PROJECT_CSS,
    "assets/css/project/b-second.css": ".oink-project-second { width: 2px; }\n",
    "assets/css/project/a-first.css": ".oink-project-first { width: 1px; }\n",
}
PROJECT_BUNDLE = PROJECT_CSS + "".join(PROJECT[name] for name in sorted(PROJECT)[1:])
SITE = {
    "hugo.yaml": """baseURL: https://example.org/
title: Stylesheet regression
theme: oink
disableKinds: [taxonomy, term, RSS, sitemap]
markup:
  highlight:
    noClasses: false
""",
    "content/_index.md": "---\ntitle: Stylesheet regression\n---\n",
    "content/docs/_index.md": "---\ntitle: Docs\n---\n",
    "content/docs/api.md": (
        '---\ntitle: API\n---\n\n{{< redoc "/spec.yaml" >}}\n'
        '\n```go\nfunc main() {}\n```\n'
    ),
    "static/spec.yaml": "openapi: 3.0.0\ninfo: {title: Probe, version: '1'}\npaths: {}\n",
}


def build(hugo: str, files: dict[str, str], environment: str) -> tuple[Path, list[str]]:
    """Build one probe site with no Sass compiler reachable; return output and diagnostics."""

    site = Path(tempfile.mkdtemp(prefix="oink-scss-"))
    tools = site / "tools"
    tools.mkdir()
    # A fresh PATH and fresh resources prevent an installed Sass compiler or a
    # previously compiled asset from making this regression pass.
    env = os.environ.copy()
    env.update(PATH=str(tools), GOWORK="off", HUGO_MODULE_WORKSPACE="off",
               HUGO_RESOURCEDIR=str(site / "resources"))
    env.pop("HUGO_MODULE_REPLACEMENTS", None)
    assert shutil.which("sass", path=env["PATH"]) is None
    for name, content in {**SITE, **files}.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    command = [hugo, "--source", str(site), "--themesDir", str(ROOT.parent),
               "--destination", str(site / "public"), "--cacheDir", str(site / "cache"),
               "--ignoreCache", "--noBuildLock", "--logLevel", "warn",
               "--environment", environment]
    result = run_hugo_process(command, env=env, text=True, capture_output=True)
    output = result.stdout + result.stderr
    if result.returncode:
        raise SystemExit(output)
    return site / "public", [line for line in output.splitlines()
                             if re.match(r"^(WARN|ERROR)\b", line)]


def stylesheet_links(page: str) -> list[str]:
    return re.findall(r'<link href="?([^" >]+\.css)"? rel="?stylesheet', page)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hugo", default="hugo", help="Hugo that builds the probe sites")
    parser.add_argument("--compiler", help="Hugo with LibSass for the freshness check; "
                                           "default: bin/build-css.py's own choice")
    parser.add_argument("--skip-freshness", action="store_true",
                        help="do not recompile the bundles; check only what a site build "
                             "does, which needs no LibSass")
    args = parser.parse_args()
    hugo = shutil.which(args.hugo)
    if not hugo:
        raise SystemExit(f"Hugo executable not found: {args.hugo}")

    callers = [f"{path.relative_to(ROOT)}:{number}"
               for path in sorted((ROOT / "layouts").rglob("*.html"))
               for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
               if SASS_CALL.search(line)]
    assert not callers, f"layouts must not call a Sass compiler: {callers}"

    # The bundles are compiled by LibSass; the probe sites below build with
    # whatever Hugo is under test, which may have no Sass compiler at all.
    if not args.skip_freshness:
        compiler = ["--hugo", args.compiler] if args.compiler else []
        fresh = subprocess.run([sys.executable, str(ROOT / "bin/build-css.py"), "--check", *compiler],
                               text=True, capture_output=True)
        if fresh.returncode:
            output = fresh.stdout + fresh.stderr
            if "No LibSass" in output:
                output += ("Here that is --compiler <path to it>. --skip-freshness runs the "
                           "site-build half alone; it does not show that the bundles are current.\n")
            raise SystemExit(output.rstrip())
    version = subprocess.run([hugo, "version"], text=True, capture_output=True).stdout.split()[1]

    built: list[Path] = []
    try:
        # Development publishes the shipped bundles unchanged.
        public, diagnostics = build(hugo, PROJECT, "development")
        built.append(public.parent)
        assert not diagnostics, "unexpected build diagnostics:\n" + "\n".join(diagnostics)
        for name in ("main", "redoc"):
            assert (public / "scss" / f"{name}.css").read_bytes() == \
                (ROOT / "assets/oink" / f"{name}.css").read_bytes(), \
                f"scss/{name}.css is not the shipped assets/oink/{name}.css"
        main_css = (public / "scss/main.css").read_text(encoding="utf-8")
        assert re.search(r"\[data-bs-theme=['\"]?dark['\"]?\] \.chroma", main_css), \
            "dark Chroma palette is missing"
        published = (public / "css/project.css").read_text(encoding="utf-8")
        assert [line for line in published.splitlines() if line] == PROJECT_BUNDLE.splitlines(), \
            f"project.css and project/*.css were not published in order: {published!r}"
        page = (public / "docs/api/index.html").read_text(encoding="utf-8")
        links = stylesheet_links(page)
        assert links[:3] == ["/scss/fontawesome.css", "/scss/main.css", "/css/project.css"], \
            f"stylesheets are missing or out of order: {links}"
        assert re.search(r'href="[^"]*/scss/redoc\.css"', page), "ReDoc stylesheet was not linked"

        # Production minifies, fingerprints and protects the same resources.
        public, diagnostics = build(hugo, {"assets/css/project/only.css": PROJECT_CSS}, "production")
        built.append(public.parent)
        assert not diagnostics, "unexpected build diagnostics:\n" + "\n".join(diagnostics)
        page = (public / "docs/api/index.html").read_text(encoding="utf-8")
        for pattern in (r"/scss/main\.min\.[0-9a-f]{64}\.css", r"/css/project\.min\.[0-9a-f]{64}\.css",
                        r"/scss/redoc\.min\.[0-9a-f]{64}\.css"):
            assert re.search(rf'href="?{pattern}"? [^>]*integrity="?sha256-', page), \
                f"production stylesheet is not fingerprinted with integrity: {pattern}"
        assert ".oink-project-probe{width:42px}" in next(
            (public / "css").glob("project.min.*.css")).read_text(encoding="utf-8")

        # Retired SCSS hooks warn by name, compile nothing and keep the site styled.
        legacy = {f"assets/scss/{name}.scss": f".oink-legacy-{index} {{ color: $primary; }}\n"
                  for index, name in enumerate(LEGACY_HOOKS)}
        public, diagnostics = build(hugo, legacy, "development")
        built.append(public.parent)
        for name in LEGACY_HOOKS:
            matching = [line for line in diagnostics
                        if f"assets/scss/{name}.scss is ignored" in line
                        and "assets/css/project.css" in line]
            assert len(matching) == 1, f"expected one warning for {name}.scss: {diagnostics}"
        assert len(diagnostics) == len(LEGACY_HOOKS), \
            "unexpected build diagnostics:\n" + "\n".join(diagnostics)
        page = (public / "docs/api/index.html").read_text(encoding="utf-8")
        assert stylesheet_links(page)[:2] == ["/scss/fontawesome.css", "/scss/main.css"]
        assert (public / "scss/main.css").read_bytes() == (ROOT / "assets/oink/main.css").read_bytes()
        assert not any("oink-legacy" in path.read_text(encoding="utf-8", errors="ignore")
                       for path in public.rglob("*.css")), "a retired SCSS hook reached the output"
    finally:
        for site in built:
            shutil.rmtree(site, ignore_errors=True)

    freshness = "bundle freshness NOT checked" if args.skip_freshness else "current bundles"
    print(f"Stylesheet checks passed: no Sass call in layouts, {freshness}, shipped main/ReDoc "
          f"CSS, project.css hook, retired SCSS hook warnings; sites built with Hugo {version} "
          "and no Sass on PATH")


if __name__ == "__main__":
    main()
