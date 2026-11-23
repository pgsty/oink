#!/usr/bin/env python3
"""Verify the theme stylesheet: plain CSS layers that Hugo alone assembles.

The stylesheet is the files under assets/css/td/, concatenated in the order
layouts/_partials/css/layers.html lists. Nothing is compiled, so a site build
needs no tool but Hugo, and this checker builds its probe sites with an empty
PATH to prove it.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from test_site import ROOT, run_hugo_process


LAYERS = ROOT / "layouts/_partials/css/layers.html"
TD = ROOT / "assets/css/td"
# These are separate stylesheets, loaded only where their component is used.
STANDALONE = {"redoc"}
COMPILER_CALL = re.compile(r"\b(?:toCSS|css\.Sass|resources\.ToCSS|css\.PostCSS|resources\.PostCSS)\b")
RETIRED_HOOKS = ("_variables_project", "_variables_project_after_bs", "_styles_project")
PROJECT_CSS = ".oink-project-probe { width: 42px; }\n"
# css/project/*.css follows css/project.css in path order.
PROJECT = {
    "assets/css/project.css": PROJECT_CSS,
    "assets/css/project/b-second.css": ".oink-project-second { width: 2px; }\n",
    "assets/css/project/a-first.css": ".oink-project-first { width: 1px; }\n",
}
PROJECT_BUNDLE = PROJECT_CSS + "".join(PROJECT[name] for name in sorted(PROJECT)[1:])
SHELL_BUNDLES = ("chrome", "landing", "search", "compare")
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
# A site-owned shell asks for the smaller stylesheets by name.
SHELL = {
    "content/shell.md": "---\ntitle: Shell\nlayout: shellprobe\n---\n",
    "layouts/shellprobe.html": (
        "{{ range slice " + " ".join(f'"{name}"' for name in SHELL_BUNDLES) + " }}"
        '{{ with partial "css/bundle.html" . }}<link rel="stylesheet" href="{{ .RelPermalink }}">{{ end }}'
        '{{ end }}{{ with partial "css/bundle.html" "no-such-stylesheet" }}{{ .RelPermalink }}{{ end }}\n'
    ),
}


def layer_lists() -> dict[str, list[str]]:
    source = LAYERS.read_text(encoding="utf-8")
    return {name: re.findall(r'"([^"]+)"', body)
            for name, body in re.findall(r'^  "([a-z]+)" \(slice\n(.*?)\n  \)', source, re.M | re.S)}


def layer_file(name: str) -> Path:
    return ROOT / "assets" / f"{name[1:]}.css" if name.startswith("/") else TD / f"{name}.css"


def check_sources() -> dict[str, list[str]]:
    """The layer lists and the files agree, and nothing needs a compiler."""

    stray = sorted(path.relative_to(ROOT).as_posix()
                   for suffix in ("*.scss", "*.sass", "*.less") for path in (ROOT / "assets").rglob(suffix))
    assert not stray, f"the stylesheet source is plain CSS; found {stray}"
    callers = [f"{path.relative_to(ROOT)}:{number}"
               for path in sorted((ROOT / "layouts").rglob("*.html"))
               for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
               if COMPILER_CALL.search(line)]
    assert not callers, f"layouts must not call a stylesheet compiler: {callers}"

    lists = layer_lists()
    assert set(lists) == {"main", *SHELL_BUNDLES}, f"unexpected stylesheets in layers.html: {sorted(lists)}"
    main = lists["main"]
    for name, layers in lists.items():
        assert len(layers) == len(set(layers)), f"{name} lists a layer twice"
        missing = [layer for layer in layers if not layer_file(layer).is_file()]
        assert not missing, f"{name} lists layers that do not exist: {missing}"
        if name != "main":
            # A smaller stylesheet reuses main's layers; it has no source of its own.
            assert set(layers) <= set(main), f"{name} lists layers that main does not load"
    listed = {layer_file(layer) for layer in main}
    orphans = sorted(path.relative_to(ROOT).as_posix() for path in TD.rglob("*.css")
                     if path not in listed and path.relative_to(TD).with_suffix("").as_posix() not in STANDALONE)
    assert not orphans, f"layers no stylesheet loads: {orphans}"
    for path in sorted(listed | {TD / f"{name}.css" for name in STANDALONE}):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*//", text, re.M) and "@import" not in text and "@use" not in text, \
            f"{path.relative_to(ROOT)} is not plain CSS that concatenates"
        assert text.count("{") == text.count("}"), f"{path.relative_to(ROOT)} has unbalanced braces"
    return lists


def build(hugo: str, files: dict[str, str], environment: str) -> tuple[Path, list[str]]:
    """Build one probe site with no other program reachable; return output and diagnostics."""

    site = Path(tempfile.mkdtemp(prefix="oink-css-"))
    tools = site / "tools"
    tools.mkdir()
    # A fresh PATH and fresh resources keep an installed tool or a cached
    # asset from standing in for the theme's own files.
    env = os.environ.copy()
    env.update(PATH=str(tools), GOWORK="off", HUGO_MODULE_WORKSPACE="off",
               HUGO_RESOURCEDIR=str(site / "resources"))
    env.pop("HUGO_MODULE_REPLACEMENTS", None)
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
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--hugo", default="hugo", help="Hugo that builds the probe sites")
    args = parser.parse_args()
    hugo = shutil.which(args.hugo)
    if not hugo:
        raise SystemExit(f"Hugo executable not found: {args.hugo}")
    lists = check_sources()
    version = subprocess.run([hugo, "version"], text=True, capture_output=True).stdout.split()[1]

    built: list[Path] = []
    try:
        # Development publishes the layers as they are, in order.
        public, diagnostics = build(hugo, PROJECT, "development")
        built.append(public.parent)
        assert not diagnostics, "unexpected build diagnostics:\n" + "\n".join(diagnostics)
        expected = "".join(layer_file(layer).read_text(encoding="utf-8") for layer in lists["main"])
        main_css = (public / "css/main.css").read_text(encoding="utf-8")
        assert main_css == expected, "css/main.css is not the main layers in their listed order"
        assert (public / "css/redoc.css").read_bytes() == (TD / "redoc.css").read_bytes()
        assert re.search(r"\[data-bs-theme=['\"]?dark['\"]?\] \.chroma", main_css), \
            "dark Chroma palette is missing"
        published = (public / "css/project.css").read_text(encoding="utf-8")
        assert [line for line in published.splitlines() if line] == PROJECT_BUNDLE.splitlines(), \
            f"project.css and project/*.css were not published in order: {published!r}"
        page = (public / "docs/api/index.html").read_text(encoding="utf-8")
        links = stylesheet_links(page)
        assert links[:3] == ["/css/fontawesome.css", "/css/main.css", "/css/project.css"], \
            f"stylesheets are missing or out of order: {links}"
        assert re.search(r'href="[^"]*/css/redoc\.css"', page), "ReDoc stylesheet was not linked"

        # Production minifies, fingerprints and protects the same resources.
        public, diagnostics = build(hugo, {"assets/css/project/only.css": PROJECT_CSS}, "production")
        built.append(public.parent)
        assert not diagnostics, "unexpected build diagnostics:\n" + "\n".join(diagnostics)
        page = (public / "docs/api/index.html").read_text(encoding="utf-8")
        for pattern in (r"/css/main\.min\.[0-9a-f]{64}\.css", r"/css/project\.min\.[0-9a-f]{64}\.css",
                        r"/css/redoc\.min\.[0-9a-f]{64}\.css"):
            assert re.search(rf'href="?{pattern}"? [^>]*integrity="?sha256-', page), \
                f"production stylesheet is not fingerprinted with integrity: {pattern}"
        assert ".oink-project-probe{width:42px}" in next(
            (public / "css").glob("project.min.*.css")).read_text(encoding="utf-8")

        # A site-owned shell gets the smaller stylesheets by name; an unknown
        # name warns. Retired SCSS hooks warn by name and reach no output.
        retired = {f"assets/scss/{name}.scss": f".oink-retired-{index} {{ color: $primary; }}\n"
                   for index, name in enumerate(RETIRED_HOOKS)}
        public, diagnostics = build(hugo, {**retired, **SHELL}, "development")
        built.append(public.parent)
        for name in RETIRED_HOOKS:
            matching = [line for line in diagnostics
                        if f"assets/scss/{name}.scss is ignored" in line
                        and "assets/css/project.css" in line]
            assert len(matching) == 1, f"expected one warning for {name}.scss: {diagnostics}"
        unknown = [line for line in diagnostics if "unknown stylesheet" in line and "no-such-stylesheet" in line]
        assert len(unknown) == 1, f"an unknown stylesheet name did not warn once: {diagnostics}"
        assert len(diagnostics) == len(RETIRED_HOOKS) + 1, \
            "unexpected build diagnostics:\n" + "\n".join(diagnostics)
        shell = (public / "shell/index.html").read_text(encoding="utf-8")
        for name in SHELL_BUNDLES:
            assert f"/css/{name}.css" in shell, f"{name} stylesheet was not published for a site-owned shell"
            assert (public / f"css/{name}.css").read_text(encoding="utf-8") == \
                "".join(layer_file(layer).read_text(encoding="utf-8") for layer in lists[name]), \
                f"css/{name}.css is not its layers in their listed order"
        assert (TD / "version-selector.css").read_text() in (public / "css/chrome.css").read_text(), \
            "a site-owned navbar lacks the version disclosure stylesheet"
        page = (public / "docs/api/index.html").read_text(encoding="utf-8")
        assert stylesheet_links(page)[:2] == ["/css/fontawesome.css", "/css/main.css"]
        assert not any("oink-retired" in path.read_text(encoding="utf-8", errors="ignore")
                       for path in public.rglob("*.css")), "a retired SCSS hook reached the output"
    finally:
        for site in built:
            shutil.rmtree(site, ignore_errors=True)

    print(f"Stylesheet checks passed: {len(lists['main'])} plain CSS layers, no compiler call, "
          f"main/ReDoc and {len(SHELL_BUNDLES)} shell stylesheets, project.css hook, retired SCSS hook "
          f"warnings; sites built with Hugo {version} and an empty PATH")


if __name__ == "__main__":
    main()
