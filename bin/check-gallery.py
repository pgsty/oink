#!/usr/bin/env python3
"""Validate the ```gallery data fence, its static fallbacks, and Image Zoom reuse."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tempfile

from runtime_assets import chunk
from test_site import build_fixture_public, fixture_config


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/site"
VALID_IMAGE = "/media/content-primitives-static.svg"
TALL_IMAGE = "/media/content-primitives-tall.svg"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def run_hugo(hugo: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([hugo, *args], cwd=ROOT, capture_output=True, text=True, check=False)


def bundle_path(public: Path, page: str) -> tuple[Path | None, str]:
    html = (public / page).read_text()
    runtime = chunk(public, html, "image-zoom")
    return (runtime.path if runtime else None), html


def image_tag(source: str, alt: str) -> str:
    match = re.search(rf'<img\b[^>]*\balt="{re.escape(alt)}"[^>]*>', source)
    return match.group(0) if match else ""


def gallery_block(source: str) -> str:
    match = re.search(r'<ul class="td-gallery[^"]*"[^>]*>[\s\S]*?</ul>', source)
    return match.group(0) if match else ""


def fence(*lines: str, attrs: str = "") -> str:
    body = "\n".join(lines)
    suffix = f" {attrs}" if attrs else ""
    return f"```gallery{suffix}\n{body}\n```\n"


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    bundle, html = bundle_path(public, "fixtures/gallery/index.html")
    disabled_bundle, disabled = bundle_path(public, "fixtures/gallery-disabled/index.html")
    markdown = (public / "fixtures/gallery/index.md").read_text()
    print_page = (public / "_print/fixtures/index.html").read_text()

    gallery = gallery_block(html)
    require(bool(gallery), "Gallery grid is missing", errors)
    for marker in (
        "A deliberately long caption that must wrap",
        "واجهة إعدادات عربية طويلة",
        "远程图片保持静态 URL",
        '<p class="td-gallery__description">Local page resource with intrinsic dimensions.</p>',
    ):
        require(marker in gallery, f"Gallery HTML fixture missing {marker}", errors)
    require(gallery.count('<li class="td-gallery__item"') == 4, "Gallery lost an item", errors)
    require(gallery.count("<img") == 4, "Gallery lost an image", errors)
    require(gallery.count('loading="lazy" decoding="async"') == 4, "Gallery loading attributes diverged", errors)
    require(html.count("data-td-image-zoom-dialog") == 1, "Gallery page did not request one Zoom dialog", errors)
    require(bundle is not None and bundle.exists(), "Gallery has no local image-zoom chunk", errors)
    if bundle and bundle.exists():
        require("data-td-image-zoom-dialog" in bundle.read_text(), "Gallery chunk omits Image Zoom", errors)
    disabled_gallery = gallery_block(disabled)
    require(disabled_gallery.count("<img") == 2, "disabled Gallery lost its images", errors)
    require("Static Gallery overview" in disabled and "Static Gallery detail" in disabled, "disabled Gallery lost content", errors)
    require("data-td-image-zoom-dialog" not in disabled, "disabled Gallery emitted a dialog", errors)
    require(disabled_bundle is None, "disabled Gallery loaded Zoom", errors)

    page_tag = image_tag(gallery, "Blue and gold local dashboard overview")
    global_tag = image_tag(gallery, "Green and violet global dashboard detail")
    static_tag = image_tag(gallery, "Tall static SVG settings overview")
    remote_tag = image_tag(gallery, "Remote deployment history view")
    for name, tag in (("page", page_tag), ("global", global_tag), ("static", static_tag), ("remote", remote_tag)):
        require(bool(tag), f"Gallery lacks the {name} image", errors)
    # The fence resolves sources through the shared resolver, so a page resource
    # becomes its permalink and carries the dimensions Hugo knows.
    require('src="/fixtures/gallery/page.png"' in page_tag, "Gallery page resource URL is wrong", errors)
    require('width="64" height="40"' in page_tag, "Gallery page resource lacks dimensions", errors)
    require('src="/media/content-primitives-global.png"' in global_tag, "Gallery global resource URL is wrong", errors)
    require('width="64" height="40"' in global_tag, "Gallery global resource lacks dimensions", errors)
    require('src="/media/content-primitives-tall.svg"' in static_tag, "Gallery static URL is wrong", errors)
    require(" width=" not in static_tag and " height=" not in static_tag, "Gallery invented static dimensions", errors)
    require('src="https://example.invalid/gallery/remote.webp?view=full"' in remote_tag, "Gallery remote URL is wrong", errors)
    require(" width=" not in remote_tag and " height=" not in remote_tag, "Gallery invented remote dimensions", errors)

    # The theme marks what it renders, so eligible items carry the Zoom marker
    # at emit time. A `{link=…}` item becomes an anchor and is not zoomable,
    # which is what the browser runtime would decide anyway.
    require(gallery.count("data-td-image-zoom") == 3, "Gallery did not mark exactly its zoomable images", errors)
    require('<a class="td-gallery__link" href="/fixtures/gallery/">' in gallery, "Gallery link item lost its anchor", errors)
    require("data-td-image-zoom" not in remote_tag, "Gallery marked a linked image as zoomable", errors)

    order = (
        "Blue and gold local dashboard overview",
        "Green and violet global dashboard detail",
        "Tall static SVG settings overview",
        "Remote deployment history view",
    )
    require([gallery.index(value) for value in order] == sorted(gallery.index(value) for value in order), "Gallery HTML order changed", errors)

    # layouts/all.md emits .RenderShortcodes, which does not run render hooks, so
    # the Markdown output is the fence source, as it is for every data fence.
    for marker in (
        "```gallery",
        "![Blue and gold local dashboard overview](page.png) # Local page resource with intrinsic dimensions.",
        "![Tall static SVG settings overview](/media/content-primitives-tall.svg) # واجهة إعدادات عربية طويلة لاختبار الالتفاف والاتجاه التلقائي",
        "![Remote deployment history view](https://example.invalid/gallery/remote.webp?view=full) # 远程图片保持静态 URL，构建过程不会下载它。 {link=/fixtures/gallery/}",
    ):
        require(marker in markdown, f"Gallery Markdown fixture missing {marker}", errors)
    require(markdown.count("![") == 4, "Gallery Markdown lost an image", errors)
    for marker in ("<ul", "<img", "td-gallery", "data-td-image-zoom", "data-zoom-src", "<dialog", "{.gallery}"):
        require(marker not in markdown, f"Gallery Markdown contains {marker}", errors)

    print_galleries = "\n".join(re.findall(r'<ul class="td-gallery[^"]*">[\s\S]*?</ul>', print_page))
    for marker in order:
        require(marker in print_galleries, f"Gallery print output missing {marker}", errors)
    require("td-gallery--static" in print_galleries, "Gallery print output is not the stacked variant", errors)
    require("![Blue and gold local dashboard overview]" not in print_page, "Gallery print output used its Markdown fallback", errors)
    for marker in ("data-td-image-zoom", "data-zoom-src", "td-image-zoom", "<dialog"):
        require(marker not in print_page, f"Gallery print output contains {marker}", errors)
    return errors


def temp_page_build(hugo: str, body: str, *, front: str = "", panic_on_warning: bool = False) -> tuple[subprocess.CompletedProcess[str], str, str]:
    with tempfile.TemporaryDirectory(prefix="oink-gallery-page-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs/gallery-test"
        content.mkdir(parents=True)
        (content / "index.md").write_text("---\ntitle: Gallery test\noutputs: [HTML, markdown]\n" + front + "---\n\n" + body)
        destination = temp_path / "public"
        extra = ["--panicOnWarning"] if panic_on_warning else []
        result = run_hugo(hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"), "--destination", str(destination), "--logLevel", "warn", *extra)
        html = ""
        markdown = ""
        if result.returncode == 0:
            html = (destination / "docs/gallery-test/index.html").read_text()
            markdown = (destination / "docs/gallery-test/index.md").read_text()
        return result, html, markdown


def check_escaping_and_forms(hugo: str) -> list[str]:
    """alt and description are plain text; a `#` in the alt needs no escaping."""
    errors: list[str] = []
    body = fence(
        f'![A "quoted" & image]({VALID_IMAGE}) # a & *description* with `backticks`',
        f"![Image only]({TALL_IMAGE})",
        f"![Issue #42 dashboard]({VALID_IMAGE}) # tracked in \\#42",
        attrs='{class="site-gallery" data-fixture="gallery" aria-label="Gallery"}',
    )
    result, html, markdown = temp_page_build(hugo, body)
    if result.returncode != 0:
        errors.append(f"Gallery escaping fixture failed to build: {result.stdout}{result.stderr}")
        return errors
    gallery = gallery_block(html)
    require('<ul class="td-gallery td-gallery--described site-gallery" aria-label="Gallery" data-fixture="gallery">' in gallery, "Gallery root attributes did not pass through", errors)
    require('alt="A &#34;quoted&#34; &amp; image"' in gallery, "Gallery alt was not HTML-escaped", errors)
    # The description is plain text, like every other public string parameter:
    # Markdown in it stays literal rather than turning into markup.
    require("a &amp; *description* with `backticks`" in gallery, "Gallery description is not plain text", errors)
    require("<em>" not in gallery and "<code>" not in gallery, "Gallery description was rendered as Markdown", errors)
    # The image is parsed before the description marker, so a hash inside the
    # alt text is ordinary text; `\#` escapes a hash inside the description.
    require('alt="Issue #42 dashboard"' in gallery, "a hash in the alt text was treated as a description marker", errors)
    require("tracked in #42" in gallery, "an escaped hash did not survive in the description", errors)
    require(gallery.count("<img") == 3, "Gallery escaping fixture lost an item", errors)
    require(gallery.count('<p class="td-gallery__description">') == 2, "Gallery description count changed", errors)
    require("```gallery" in markdown, "Gallery Markdown output is not the fence source", errors)
    return errors


def check_invalid_cases(hugo: str) -> list[str]:
    """Invalid fences warn with the offending line and fail strict builds."""
    errors: list[str] = []
    cases = (
        ("no-image", fence("just some text"), "must start with a Markdown image"),
        ("bare-text", fence(f"![Alt]({VALID_IMAGE}) trailing words"), "must start with #"),
        ("empty-description", fence(f"![Alt]({VALID_IMAGE}) #"), "must not be empty"),
        ("unknown-attribute", fence(f"![Alt]({VALID_IMAGE}) {{bogus=1}}"), "unknown attribute"),
        ("duplicate-attribute", fence(f"![Alt]({VALID_IMAGE}) {{link=/a/ link=/b/}}"), "is set twice"),
        ("malformed-attribute", fence(f"![Alt]({VALID_IMAGE}) {{link}}"), "malformed attributes"),
        ("empty-fence", "```gallery\n```\n", "requires at least one image"),
    )
    for name, body, expected in cases:
        result, _, _ = temp_page_build(hugo, body)
        output = f"{result.stdout}{result.stderr}"
        require(expected in output, f"Gallery invalid case {name} lacks {expected!r}: {output[:400]}", errors)
        strict, _, _ = temp_page_build(hugo, body, panic_on_warning=True)
        require(strict.returncode != 0, f"Gallery invalid case {name} survived --panicOnWarning", errors)
    return errors


def check_subpath(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-gallery-subpath-") as temp:
        destination = Path(temp) / "public"
        result = run_hugo(hugo, "--source", str(FIXTURE), "--destination", str(destination), "--baseURL", "https://example.org/manual/", "--config", fixture_config(), "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"Gallery subpath fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        gallery = gallery_block((destination / "fixtures/gallery/index.html").read_text())
        for marker in (
            'src="/manual/fixtures/gallery/page.png"',
            'src="/manual/media/content-primitives-global.png"',
            'src="/manual/media/content-primitives-tall.svg"',
            'src="https://example.invalid/gallery/remote.webp?view=full"',
            'href="/manual/fixtures/gallery/"',
        ):
            require(marker in gallery, f"Gallery subpath fixture missing {marker}", errors)
    return errors


def check_rss_output(hugo: str) -> list[str]:
    """RenderShortcodes keeps the fence source; the section feed renders it statically."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-gallery-rss-") as temp:
        site = Path(temp)
        item = site / "content/docs/item"
        item.mkdir(parents=True)
        (site / "content/docs/_index.md").write_text("---\ntitle: Docs\n---\n")
        (item / "index.md").write_text(
            "---\ntitle: Gallery feed item\ndate: 2026-08-11\noutputs: [HTML, markdown]\n---\n\n"
            "Before gallery with enough ordinary summary words to exercise the cached generic section feed output.\n\n"
            + fence(
                f"![RSS first]({VALID_IMAGE}) # First description",
                f"![RSS second]({TALL_IMAGE})",
            )
            + "\n"
            '<p><img src="/media/content-primitives-static.svg" alt="Boundary fixture" '
            'data-td-image-zoom-extra="keep" data-no-zoom-extra="keep"></p>\n'
        )
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\ntitle: Gallery RSS fixture\n"
            f"theme: {ROOT.name}\n"
            "disableKinds: [sitemap, taxonomy, term]\n"
            "outputs:\n  home: [HTML, RSS]\n  section: [HTML, RSS]\n  page: [HTML, markdown]\n"
            "params:\n  ui:\n    image_zoom: true\n"
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
        for marker in ("Before gallery with enough ordinary summary words", "RSS first", "First description", "RSS second", "&lt;ul class=&#34;td-gallery"):
            require(marker in source, f"Gallery RSS fixture missing {marker}", errors)
        require(source.index("RSS first") < source.index("RSS second"), "Gallery RSS order changed", errors)
        for marker in ('data-td-image-zoom-extra=&#34;keep&#34;', 'data-no-zoom-extra=&#34;keep&#34;'):
            require(marker in source, f"static filter damaged similar attribute {marker}", errors)
        for marker in ("![RSS first]", "data-zoom-src", "data-td-image-zoom-dialog", "<dialog"):
            require(marker not in source, f"Gallery RSS fixture contains {marker}", errors)
        require(not re.search(r"data-td-image-zoom(?:=|\s|&gt;)", source), "Gallery RSS fixture contains the exact Zoom eligibility attribute", errors)
        require(not re.search(r"data-no-zoom(?:=|\s|&gt;)", source), "Gallery RSS fixture contains the exact no-Zoom attribute", errors)
        markdown = (destination / "docs/item/index.md").read_text()
        require("```gallery" in markdown and f"![RSS first]({VALID_IMAGE}) # First description" in markdown, "Gallery Markdown output is not the fence source", errors)
    return errors


def zoom_site_config(enabled: bool | None) -> str:
    config = (
        "baseURL: https://example.org/\ntitle: Gallery Zoom fixture\n"
        f"theme: {ROOT.name}\n"
        "disableKinds: [RSS, sitemap, taxonomy, term]\n"
        "markup:\n  goldmark:\n    parser:\n      wrapStandAloneImageWithinParagraph: false\n      attribute:\n        block: true\n"
    )
    if enabled is not None:
        config += f"params:\n  ui:\n    image_zoom: {str(enabled).lower()}\n"
    return config


def check_zoom_reuse(hugo: str) -> list[str]:
    errors: list[str] = []
    described = fence(
        f"![First Zoom image]({VALID_IMAGE}) # with description",
        f"![Second Zoom image]({TALL_IMAGE}) # with description",
    )
    cases = (
        ("default-off", None, None, described, False),
        ("site-on", True, None, described, True),
        ("page-false-wins", True, False, described, False),
        ("empty-alt-no-candidate", True, None, fence(f"![]({VALID_IMAGE}) # decorative only"), False),
        ("image-only-items", True, None, fence(f"![One]({VALID_IMAGE})", f"![Two]({TALL_IMAGE})"), True),
        ("linked-items-no-candidate", True, None, fence(f"![One]({VALID_IMAGE}) {{link=/docs/}}"), False),
    )
    for name, site_enabled, page_enabled, body, expected in cases:
        with tempfile.TemporaryDirectory(prefix=f"oink-gallery-zoom-{name}-") as temp:
            site = Path(temp)
            (site / "content/docs").mkdir(parents=True)
            front = "---\ntitle: Gallery Zoom\n"
            if page_enabled is not None:
                front += f"image_zoom: {str(page_enabled).lower()}\n"
            front += "---\n\n"
            (site / "content/docs/index.md").write_text(front + body)
            (site / "hugo.yaml").write_text(zoom_site_config(site_enabled))
            destination = site / "public"
            result = run_hugo(hugo, "--source", str(site), "--themesDir", str(ROOT.parent), "--destination", str(destination), "--logLevel", "warn")
            if result.returncode != 0:
                errors.append(f"Gallery Zoom case {name} failed: {result.stdout}{result.stderr}")
                continue
            bundle, page = bundle_path(destination, "docs/index.html")
            require(bool(gallery_block(page)), f"Gallery Zoom case {name} lost its grid", errors)
            require(("data-td-image-zoom-dialog" in page) == expected, f"Gallery Zoom case {name} dialog state is wrong", errors)
            require((bundle is not None and bundle.exists()) == expected, f"Gallery Zoom case {name} runtime state is wrong", errors)
            if bundle and bundle.exists():
                require("data-td-image-zoom-dialog" in bundle.read_text(), f"Gallery Zoom case {name} runtime content is wrong", errors)
            if expected:
                require(page.count("data-td-image-zoom-dialog") == 1, "Gallery emitted duplicate dialogs", errors)
    return errors


def check_template_contracts() -> list[str]:
    errors: list[str] = []
    styles = (ROOT / "assets/scss/td/_gallery.scss").read_text()
    markers = (ROOT / "assets/scss/td/_markers.scss").read_text()
    candidate = (ROOT / "layouts/_partials/content/image-zoom-candidate.html").read_text()
    static_output = (ROOT / "layouts/_partials/content/static-image-output.html").read_text()
    scripts = (ROOT / "layouts/_partials/scripts.html").read_text()
    hook = (ROOT / "layouts/_markup/render-image.html").read_text()
    runtime = (ROOT / "assets/js/image-zoom.js").read_text()
    ci = (ROOT / ".github/workflows/ci.yml").read_text()

    for relative in ("layouts/_shortcodes/gallery.html", "layouts/_shortcodes/gallery/image.html"):
        require(not (ROOT / relative).exists(), f"{relative} must stay deleted", errors)
    require((ROOT / "layouts/_markup/render-codeblock-gallery.html").exists(), "the gallery fence hook is missing", errors)
    require((ROOT / "layouts/_partials/content/gallery-parse.html").exists(), "the gallery parser is missing", errors)
    # The fence marks its own images, so neither the build-time scan nor the
    # runtime needs a gallery-shaped structural exception any more.
    require("ul.gallery" not in candidate, "Zoom candidate scan still special-cases gallery lists", errors)
    require("ul.gallery" not in runtime, "the Zoom runtime still special-cases gallery lists", errors)
    require("ul.gallery" not in markers, "_markers.scss still styles the removed gallery list", errors)
    require("data-td-image-zoom" in hook, "render-image hook does not mark eligible block images for Zoom", errors)
    require("$policy.generic" in (ROOT / "layouts/_markup/render-codeblock-gallery.html").read_text(), "Gallery hook drops generic attributes", errors)
    require("js/gallery" not in scripts and not (ROOT / "assets/js/gallery.js").exists(), "Gallery added a second runtime", errors)
    require("data-td-image-zoom" in static_output, "static output filter does not remove Zoom eligibility", errors)
    require("(\\s|/?>)" in static_output and '"$1"' in static_output, "static output filter lacks exact attribute boundaries", errors)
    for marker in (".td-gallery", "grid-template-columns: repeat(auto-fit", "forced-colors", "@media print", "break-inside"):
        require(marker in styles, f"Gallery styles lack {marker}", errors)
    require("python3 bin/check-gallery.py" in ci, "CI does not run Gallery checks", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path)
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    public = args.public
    if public is None:
        public, result = build_fixture_public(args.hugo)
        if result.returncode != 0:
            print(f"private fixture build failed: {result.stdout}{result.stderr}")
            return 1

    errors = (
        check_outputs(public)
        + check_escaping_and_forms(args.hugo)
        + check_invalid_cases(args.hugo)
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
