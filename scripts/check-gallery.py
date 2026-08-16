#!/usr/bin/env python3
"""Validate the native Gallery list (`{.gallery}`), its static fallbacks, and Image Zoom reuse."""

from __future__ import annotations

import argparse
from html import unescape
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
MAIN_SCRIPT = re.compile(r'<script src="([^"]*/js/main-[^"]+\.js)"[^>]*>')
VALID_IMAGE = "/media/content-primitives-static.svg"
TALL_IMAGE = "/media/content-primitives-tall.svg"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def run_hugo(hugo: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([hugo, *args], cwd=ROOT, capture_output=True, text=True, check=False)


def bundle_path(public: Path, page: str) -> tuple[Path | None, str]:
    source = (public / page).read_text()
    match = MAIN_SCRIPT.search(source)
    if not match:
        return None, source
    relative = unescape(match.group(1)).split("?", 1)[0].lstrip("/")
    return public / relative, source


def image_tag(source: str, alt: str) -> str:
    match = re.search(rf'<img\b[^>]*\balt="{re.escape(alt)}"[^>]*>', source)
    return match.group(0) if match else ""


def gallery_block(source: str) -> str:
    match = re.search(r'<ul class="gallery">[\s\S]*?</ul>', source)
    return match.group(0) if match else ""


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    bundle, html = bundle_path(public, "docs/gallery/index.html")
    disabled_bundle, disabled = bundle_path(public, "docs/gallery-disabled/index.html")
    markdown = (public / "docs/gallery/index.md").read_text()
    print_page = (public / "_print/docs/index.html").read_text()

    gallery = gallery_block(html)
    require(bool(gallery), "Gallery list is missing", errors)
    for marker in (
        "A deliberately long caption that must wrap",
        "واجهة إعدادات عربية طويلة",
        "远程图片保持静态 URL",
        " — Local page resource with intrinsic dimensions.",
    ):
        require(marker in gallery, f"Gallery HTML fixture missing {marker}", errors)
    require(gallery.count("<li>") == 4, "Gallery lost an item", errors)
    require(gallery.count("<img") == 4, "Gallery lost an image", errors)
    require(gallery.count('loading="lazy" decoding="async"') == 4, "Gallery loading attributes diverged", errors)
    require(html.count("data-td-image-zoom-dialog") == 1, "Gallery page did not request one Zoom dialog", errors)
    require(bundle is not None and bundle.exists(), "Gallery has no local main bundle", errors)
    if bundle and bundle.exists():
        require("data-td-image-zoom-dialog" in bundle.read_text(), "Gallery bundle omits Image Zoom", errors)
    disabled_gallery = gallery_block(disabled)
    require(disabled_gallery.count("<img") == 2, "disabled Gallery lost its images", errors)
    require("Static Gallery overview" in disabled and "Static Gallery detail" in disabled, "disabled Gallery lost content", errors)
    require("data-td-image-zoom-dialog" not in disabled, "disabled Gallery emitted a dialog", errors)
    require(disabled_bundle is not None and disabled_bundle.exists(), "disabled Gallery has no main bundle", errors)
    if disabled_bundle and disabled_bundle.exists():
        require("data-td-image-zoom-dialog" not in disabled_bundle.read_text(), "disabled Gallery loaded Zoom", errors)
    require(bundle != disabled_bundle, "enabled and disabled Gallery reused one bundle target", errors)

    page_tag = image_tag(gallery, "Blue and gold local dashboard overview")
    global_tag = image_tag(gallery, "Green and violet global dashboard detail")
    static_tag = image_tag(gallery, "Tall static SVG settings overview")
    remote_tag = image_tag(gallery, "Remote deployment history view")
    for name, tag in (("page", page_tag), ("global", global_tag), ("static", static_tag), ("remote", remote_tag)):
        require(bool(tag), f"Gallery lacks the {name} image", errors)
    require('src="/docs/gallery/page.png"' in page_tag, "Gallery page resource URL is wrong", errors)
    require('width="64" height="40"' in page_tag, "Gallery page resource lacks dimensions", errors)
    require('src="/media/content-primitives-global.png"' in global_tag, "Gallery global resource URL is wrong", errors)
    require('width="64" height="40"' in global_tag, "Gallery global resource lacks dimensions", errors)
    require('src="/media/content-primitives-tall.svg"' in static_tag, "Gallery static URL is wrong", errors)
    require(" width=" not in static_tag and " height=" not in static_tag, "Gallery invented static dimensions", errors)
    require('src="https://example.invalid/gallery/remote.webp?view=full"' in remote_tag, "Gallery remote URL is wrong", errors)
    require(" width=" not in remote_tag and " height=" not in remote_tag, "Gallery invented remote dimensions", errors)

    order = (
        "Blue and gold local dashboard overview",
        "Green and violet global dashboard detail",
        "Tall static SVG settings overview",
        "Remote deployment history view",
    )
    require([gallery.index(value) for value in order] == sorted(gallery.index(value) for value in order), "Gallery HTML order changed", errors)

    for marker in (
        "- ![Blue and gold local dashboard overview](page.png) — Local page resource with intrinsic dimensions.",
        "- ![Green and violet global dashboard detail](media/content-primitives-global.png) — A deliberately long caption",
        "- ![Tall static SVG settings overview](/media/content-primitives-tall.svg) — واجهة إعدادات عربية طويلة لاختبار الالتفاف والاتجاه التلقائي",
        "- ![Remote deployment history view](https://example.invalid/gallery/remote.webp?view=full) — 远程图片保持静态 URL，构建过程不会下载它。",
        "{.gallery}",
    ):
        require(marker in markdown, f"Gallery Markdown fixture missing {marker}", errors)
    require(markdown.count("![") == 4, "Gallery Markdown lost an image", errors)
    for marker in ("<ul", "<img", "td-image", "data-td-image-zoom", "data-zoom-src", "<dialog"):
        require(marker not in markdown, f"Gallery Markdown contains {marker}", errors)

    print_galleries = "\n".join(re.findall(r'<ul class="gallery">[\s\S]*?</ul>', print_page))
    for marker in order:
        require(marker in print_galleries, f"Gallery print output missing {marker}", errors)
    require("![Blue and gold local dashboard overview]" not in print_page, "Gallery print output used its Markdown fallback", errors)
    for marker in ("data-td-image-zoom", "data-zoom-src", "td-image-zoom", "<dialog"):
        require(marker not in print_page, f"Gallery print output contains {marker}", errors)
    return errors


def temp_page_build(hugo: str, body: str, *, front: str = "") -> tuple[subprocess.CompletedProcess[str], str, str]:
    with tempfile.TemporaryDirectory(prefix="oink-gallery-page-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs/gallery-test"
        content.mkdir(parents=True)
        (content / "index.md").write_text("---\ntitle: Gallery test\noutputs: [HTML, markdown]\n" + front + "---\n\n" + body)
        destination = temp_path / "public"
        result = run_hugo(hugo, "--source", str(EXAMPLE), "--contentDir", str(temp_path / "content"), "--destination", str(destination), "--logLevel", "warn")
        html = ""
        markdown = ""
        if result.returncode == 0:
            html = (destination / "docs/gallery-test/index.html").read_text()
            markdown = (destination / "docs/gallery-test/index.md").read_text()
        return result, html, markdown


def check_escaping_and_forms(hugo: str) -> list[str]:
    """Captions are Markdown; alt is HTML-escaped; image-only items are block images."""
    errors: list[str] = []
    body = (
        f'- ![A "quoted" & image]({VALID_IMAGE}) — a &amp; *caption* with `code`\n'
        f'- ![Image only]({TALL_IMAGE})\n'
        f"- ![Loose item]({VALID_IMAGE})\n\n  A loose caption paragraph.\n"
        "{.gallery}\n"
    )
    result, html, markdown = temp_page_build(hugo, body)
    if result.returncode != 0:
        errors.append(f"Gallery escaping fixture failed to build: {result.stdout}{result.stderr}")
        return errors
    gallery = gallery_block(html)
    # Goldmark's typographer turns "quoted" into curly quotes; & must stay escaped.
    require('alt="A “quoted” &amp; image"' in gallery, "Gallery alt was not HTML-escaped", errors)
    require("a &amp; <em>caption</em> with <code>code</code>" in gallery, "Gallery caption is not Markdown", errors)
    require('<img class="td-image" src="/media/content-primitives-tall.svg" alt="Image only"' in gallery, "an image-only item is not a block image", errors)
    require("A loose caption paragraph." in gallery, "loose gallery items lost their caption paragraph", errors)
    require(gallery.count("<img") == 3, "Gallery escaping fixture lost an item", errors)
    require('- ![A "quoted" & image]' in markdown and "{.gallery}" in markdown, "Gallery Markdown output is not the source list", errors)
    return errors


def check_subpath(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-gallery-subpath-") as temp:
        destination = Path(temp) / "public"
        result = run_hugo(hugo, "--source", str(EXAMPLE), "--destination", str(destination), "--baseURL", "https://example.org/manual/", "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"Gallery subpath fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        gallery = gallery_block((destination / "docs/gallery/index.html").read_text())
        for marker in (
            'src="/manual/docs/gallery/page.png"',
            'src="/manual/media/content-primitives-global.png"',
            'src="/manual/media/content-primitives-tall.svg"',
            'src="https://example.invalid/gallery/remote.webp?view=full"',
        ):
            require(marker in gallery, f"Gallery subpath fixture missing {marker}", errors)
    return errors


def check_rss_output(hugo: str) -> list[str]:
    """RenderShortcodes keeps the list source; the section feed renders it statically."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-gallery-rss-") as temp:
        site = Path(temp)
        item = site / "content/docs/item"
        item.mkdir(parents=True)
        (site / "content/docs/_index.md").write_text("---\ntitle: Docs\n---\n")
        (item / "index.md").write_text(
            "---\ntitle: Gallery feed item\ndate: 2026-08-11\noutputs: [HTML, markdown]\n---\n\n"
            "Before gallery with enough ordinary summary words to exercise the cached generic section feed output.\n\n"
            f"- ![RSS first]({VALID_IMAGE}) — First caption\n"
            f"- ![RSS second]({TALL_IMAGE})\n"
            "{.gallery}\n\n"
            '<p><img src="/media/content-primitives-static.svg" alt="Boundary fixture" '
            'data-td-image-zoom-extra="keep" data-no-zoom-extra="keep"></p>\n'
        )
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\ntitle: Gallery RSS fixture\n"
            f"theme: {ROOT.name}\n"
            "disableKinds: [sitemap, taxonomy, term]\n"
            "outputs:\n  home: [HTML, RSS]\n  section: [HTML, RSS]\n  page: [HTML, markdown]\n"
            "params:\n  ui:\n    image_zoom:\n      enable: true\n"
            "markup:\n  goldmark:\n    renderer:\n      unsafe: true\n    parser:\n      wrapStandAloneImageWithinParagraph: false\n      attribute:\n        block: true\n"
        )
        destination = site / "public"
        result = run_hugo(hugo, "--source", str(site), "--themesDir", str(ROOT.parent), "--destination", str(destination), "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"Gallery RSS fixture failed: {result.stdout}{result.stderr}")
            return errors
        source = (destination / "docs/index.xml").read_text()
        page = (destination / "docs/item/index.html").read_text()
        require("data-td-image-zoom-dialog" in page, "Gallery item page did not request Zoom", errors)
        for marker in ("Before gallery with enough ordinary summary words", "RSS first", "First caption", "RSS second", '&lt;ul class=&#34;gallery&#34;&gt;'):
            require(marker in source, f"Gallery RSS fixture missing {marker}", errors)
        require(source.index("RSS first") < source.index("RSS second"), "Gallery RSS order changed", errors)
        for marker in ('data-td-image-zoom-extra=&#34;keep&#34;', 'data-no-zoom-extra=&#34;keep&#34;'):
            require(marker in source, f"static filter damaged similar attribute {marker}", errors)
        for marker in ("![RSS first]", "data-zoom-src", "data-td-image-zoom-dialog", "<dialog"):
            require(marker not in source, f"Gallery RSS fixture contains {marker}", errors)
        require(not re.search(r"data-td-image-zoom(?:=|\s|&gt;)", source), "Gallery RSS fixture contains the exact Zoom eligibility attribute", errors)
        require(not re.search(r"data-no-zoom(?:=|\s|&gt;)", source), "Gallery RSS fixture contains the exact no-Zoom attribute", errors)
        markdown = (destination / "docs/item/index.md").read_text()
        require(f"- ![RSS first]({VALID_IMAGE}) — First caption" in markdown and "{.gallery}" in markdown, "Gallery Markdown output is not the source list", errors)
    return errors


def zoom_site_config(enabled: bool | None) -> str:
    config = (
        "baseURL: https://example.org/\ntitle: Gallery Zoom fixture\n"
        f"theme: {ROOT.name}\n"
        "disableKinds: [RSS, sitemap, taxonomy, term]\n"
        "markup:\n  goldmark:\n    parser:\n      wrapStandAloneImageWithinParagraph: false\n      attribute:\n        block: true\n"
    )
    if enabled is not None:
        config += f"params:\n  ui:\n    image_zoom:\n      enable: {str(enabled).lower()}\n"
    return config


def check_zoom_reuse(hugo: str) -> list[str]:
    errors: list[str] = []
    captioned = f"- ![First Zoom image]({VALID_IMAGE}) — with caption\n- ![Second Zoom image]({TALL_IMAGE}) — with caption\n{{.gallery}}\n"
    cases = (
        ("default-off", None, None, captioned, False),
        ("site-on", True, None, captioned, True),
        ("page-false-wins", True, False, captioned, False),
        ("empty-alt-no-candidate", True, None, f"- ![]({VALID_IMAGE}) — decorative only\n{{.gallery}}\n", False),
        ("image-only-items", True, None, f"- ![One]({VALID_IMAGE})\n- ![Two]({TALL_IMAGE})\n{{.gallery}}\n", True),
    )
    for name, site_enabled, page_enabled, body, expected in cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-gallery-zoom-{name}-") as temp:
            site = Path(temp)
            (site / "content/docs").mkdir(parents=True)
            front = "---\ntitle: Gallery Zoom\n"
            if page_enabled is not None:
                front += f"params:\n  ui:\n    image_zoom:\n      enable: {str(page_enabled).lower()}\n"
            front += "---\n\n"
            (site / "content/docs/index.md").write_text(front + body)
            (site / "hugo.yaml").write_text(zoom_site_config(site_enabled))
            destination = site / "public"
            result = run_hugo(hugo, "--source", str(site), "--themesDir", str(ROOT.parent), "--destination", str(destination), "--logLevel", "warn")
            if result.returncode != 0:
                errors.append(f"Gallery Zoom case {name} failed: {result.stdout}{result.stderr}")
                continue
            bundle, page = bundle_path(destination, "docs/index.html")
            require(bool(gallery_block(page)), f"Gallery Zoom case {name} lost its list", errors)
            require(("data-td-image-zoom-dialog" in page) == expected, f"Gallery Zoom case {name} dialog state is wrong", errors)
            require(bundle is not None and bundle.exists(), f"Gallery Zoom case {name} lacks a bundle", errors)
            if bundle and bundle.exists():
                require(("data-td-image-zoom-dialog" in bundle.read_text()) == expected, f"Gallery Zoom case {name} bundle state is wrong", errors)
            if expected:
                require(page.count("data-td-image-zoom-dialog") == 1, "Gallery emitted duplicate dialogs", errors)
    return errors


def check_template_contracts() -> list[str]:
    errors: list[str] = []
    styles = (ROOT / "assets/scss/td/_markers.scss").read_text()
    candidate = (ROOT / "layouts/_partials/content/image-zoom-candidate.html").read_text()
    static_output = (ROOT / "layouts/_partials/content/static-image-output.html").read_text()
    scripts = (ROOT / "layouts/_partials/scripts.html").read_text()
    hook = (ROOT / "layouts/_markup/render-image.html").read_text()
    ci = (ROOT / ".github/workflows/ci.yml").read_text()

    for relative in ("layouts/_shortcodes/gallery.html", "layouts/_shortcodes/gallery/image.html"):
        require(not (ROOT / relative).exists(), f"{relative} must stay deleted", errors)
    require('<ul class="gallery' in candidate, "Zoom candidate scan does not consider native gallery lists", errors)
    require("data-td-image-zoom" in hook, "render-image hook does not mark eligible block images for Zoom", errors)
    require("js/gallery" not in scripts and not (ROOT / "assets/js/gallery.js").exists(), "Gallery added a second runtime", errors)
    require("data-td-image-zoom" in static_output, "static output filter does not remove Zoom eligibility", errors)
    require("(\\s|/?>)" in static_output and '"$1"' in static_output, "static output filter lacks exact attribute boundaries", errors)
    for marker in ("ul.gallery", "grid-template-columns: repeat(auto-fit", "forced-colors", "@media print", "break-inside"):
        require(marker in styles, f"Gallery styles lack {marker}", errors)
    require("python3 scripts/check-gallery.py" in ci, "CI does not run Gallery checks", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, default=EXAMPLE / "public")
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    errors = (
        check_outputs(args.public)
        + check_escaping_and_forms(args.hugo)
        + check_subpath(args.hugo)
        + check_rss_output(args.hugo)
        + check_zoom_reuse(args.hugo)
        + check_template_contracts()
    )
    if errors:
        print("Gallery checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Gallery checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
