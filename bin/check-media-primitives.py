#!/usr/bin/env python3
"""Validate shared image resolution and the render-image hook (all image forms)."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import struct
import tempfile

from runtime_assets import combined_source
from test_site import (
    build_fixture_public,
    fixture_config,
    fixture_media_config,
    run_hugo_process,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/site"
PAGE_IMAGE = ROOT / "tests/site/content/fixtures/media-primitives/page.png"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def run_hugo(hugo: str, *args: str) -> subprocess.CompletedProcess[str]:
    return run_hugo_process([hugo, *args], cwd=ROOT, capture_output=True, text=True, check=False)


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    page = (public / "fixtures/media-primitives/index.html").read_text()
    markdown = (public / "fixtures/media-primitives/index.md").read_text()
    print_page = (public / "_print/fixtures/index.html").read_text()

    def feature_bundle(source: str) -> str:
        return combined_source(public, source)

    for marker in (
        # attribute line + {command=/options=}: processed figure, Zoom marker
        # carrying the full-size original
        '<figure class="td-figure">',
        # resource metadata: alt from params.alt, byline inside the figcaption
        '<span class="td-fig-caption">Alt text and the byline come from the resource metadata.</span>',
        '<small class="td-figure__byline">OINK fixture byline</small>',
        # plain block image: bare img, advisory title kept, zoom marker
        '<img class="td-image" src="/fixtures/media-primitives/page.png" alt="Blue and gold page-resource test pattern" title="Advisory title" width="64" height="40" data-td-image-zoom loading="lazy" decoding="async">',
        # block image + {caption=} becomes a figure
        '<img src="/media/content-primitives-static.svg" alt="Static preview" data-td-image-zoom loading="lazy" decoding="async">',
        '<figcaption> <span class="td-fig-caption">A static image with a caption becomes a figure</span></figcaption>',
        # {link=} wraps the image in an anchor inside the figure and is not zoomable
        '<a class="td-figure__link" href="/docs/"><img src="/fixtures/media-primitives/page.png" alt="Blue and gold page-resource test pattern" width="64" height="40" loading="lazy" decoding="async"></a>',
        '<span class="td-fig-caption">A linked figure keeps the anchor inside the figure</span>',
        '<span class="td-fig-caption">The attribute line can process too</span>',
    ):
        require(marker in page, f"HTML media fixture missing {marker}", errors)
    # Hugo owns derivative hashes. Pin source, markup, dimensions and a real
    # generated PNG instead of one version's opaque processing cache key.
    for prefix, alt, width, height, zoom, css in (
        ("/fixtures/media-primitives/page", "Blue and gold page-resource test pattern", 48, 30, '/fixtures/media-primitives/page.png', ""),
        ("/media/content-primitives-global", "Green and violet global-resource test pattern", 32, 20, '/media/content-primitives-global.png', ""),
        ("/fixtures/media-primitives/page", "", 24, 24, "", ' class="td-image"'),
    ):
        zoom_attr = f' data-td-image-zoom="{zoom}"' if zoom else ""
        pattern = (rf'<img{css} src="({re.escape(prefix)}_hu_[0-9a-f]+\.png)"'
                   + re.escape(f' alt="{alt}" width="{width}" height="{height}"{zoom_attr} loading="lazy" decoding="async">'))
        match = re.search(pattern, page)
        require(match is not None, f"processed image lost its source or attributes: {prefix} {width}x{height}", errors)
        if match:
            generated = public / match.group(1).lstrip("/")
            require(generated.is_file(), f"processed image was not published: {generated}", errors)
            if generated.is_file():
                data = generated.read_bytes()
                require(data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24
                        and struct.unpack(">II", data[16:24]) == (width, height),
                        f"processed image dimensions differ from its HTML: {generated}", errors)
    # The retired shortcode owned this class; nothing emits it any more.
    require("td-figure--processed" not in page, "the retired processed-figure class survived", errors)
    # The byline belongs to the resource, so every captioned figure built from
    # that resource carries it — the behaviour the retired shortcode had.
    require(page.count("td-figure__byline") == 4, "the resource byline is not rendered on every figure of that resource", errors)
    require(page.count('loading="lazy" decoding="async"') == 8, "images lack stable loading attributes", errors)
    require("td-imgproc" not in page and "card-img-top" not in page, "legacy imgproc markup survived", errors)
    require("resources.GetRemote" not in page, "rendered media output leaked template code", errors)
    require('id="td-drawio-config"' in page and "drawioframe" in feature_bundle(page),
            "a page with PNG/SVG candidates did not load the Draw.io runtime", errors)
    badge = (public / "docs/badge/index.html").read_text()
    require('id="td-drawio-config"' not in badge and "drawioframe" not in feature_bundle(badge),
            "Draw.io leaked onto a page without image candidates", errors)

    # Every image form is now a render hook, and layouts/all.md emits
    # .RenderShortcodes, which does not run hooks — so Markdown output is the
    # page source for all of them, with the original (unprocessed) src.
    for marker in (
        '![Blue and gold page-resource test pattern](page.png)\n{command="Fit" options="48x32"',
        '![Green and violet global-resource test pattern](media/content-primitives-global.png)',
        '![Blue and gold page-resource test pattern](page.png "Advisory title")',
        "![Static preview](/media/content-primitives-static.svg)",
        '{caption="A static image with a caption becomes a figure"}',
        '{caption="A linked figure keeps the anchor inside the figure" link="/docs/"}',
    ):
        require(marker in markdown, f"Markdown media fixture missing {marker}", errors)
    for marker in ("<figure", "<img", "td-figure", "data-td-image-zoom"):
        require(marker not in markdown, f"Markdown media output contains {marker}", errors)
    require(markdown.count("![") == 8, "Markdown media output lost image order", errors)
    require("_hu_" not in markdown, "Markdown media output leaked a processed derivative URL", errors)

    for marker in (
        "Blue and gold page-resource test pattern",
        "Green and violet global-resource test pattern",
        "page_hu_",
        "content-primitives-global_hu_",
        "OINK fixture byline",
        '<figure class="td-figure">',
        "A static image with a caption becomes a figure",
    ):
        require(marker in print_page, f"print media fixture missing {marker}", errors)
    require("data-td-image-zoom" not in print_page, "print media output kept interactive zoom attributes", errors)
    return errors


RESOLVER_SHORTCODE = r'''{{- $resolved := partial "content/image-resolve.html" (dict
  "name" .Name "position" .Position "page" .Page "src" (.Get "src")
  "hasAlt" true "alt" (.Get "alt") "requireAlt" true
) -}}
<span class="media-resolve-fixture"
  data-kind="{{ $resolved.kind }}"
  data-media-type="{{ $resolved.mediaType }}"
  data-processable="{{ $resolved.processable }}"
  data-width="{{ $resolved.width }}"
  data-height="{{ $resolved.height }}"
  data-full-src="{{ $resolved.fullSrc }}"><img src="{{ $resolved.src }}" alt="{{ $resolved.alt }}"></span>
'''


def check_resolver_matrix(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-media-resolver-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs/resolver"
        layouts = temp_path / "layouts/_shortcodes"
        content.mkdir(parents=True)
        layouts.mkdir(parents=True)
        shutil.copyfile(PAGE_IMAGE, content / "page.png")
        (layouts / "media-resolve-test.html").write_text(RESOLVER_SHORTCODE)
        (content / "index.md").write_text(
            "---\ntitle: Resolver matrix\n---\n\n"
            '{{< media-resolve-test src="page.png" alt="Page raster" >}}\n'
            '{{< media-resolve-test src="media/content-primitives-global.png" alt="Global raster" >}}\n'
            '{{< media-resolve-test src="media/content-primitives-global.svg" alt="Global SVG" >}}\n'
            '{{< media-resolve-test src="/media/content-primitives-static.svg" alt="Static SVG" >}}\n'
            '{{< media-resolve-test src="https://example.invalid/remote.png?fixture=1" alt="Remote raster" >}}\n'
        )
        destination = temp_path / "public"
        result = run_hugo(hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"), "--layoutDir", str(temp_path / "layouts"), "--destination", str(destination), "--baseURL", "https://example.org/manual/", "--config", fixture_media_config(), "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"resolver matrix failed to build: {result.stdout}{result.stderr}")
            return errors
        page = (destination / "docs/resolver/index.html").read_text()
        compact_page = " ".join(page.split())
        for marker in (
            'data-kind="page" data-media-type="image/png" data-processable="true" data-width="64" data-height="40" data-full-src="/manual/docs/resolver/page.png"',
            '<img src="/manual/docs/resolver/page.png" alt="Page raster">',
            'data-kind="global" data-media-type="image/png" data-processable="true" data-width="64" data-height="40" data-full-src="/manual/media/content-primitives-global.png"',
            'data-kind="global" data-media-type="image/svg&#43;xml" data-processable="false" data-width="0" data-height="0" data-full-src="/manual/media/content-primitives-global.svg"',
            'data-kind="static" data-media-type="image/svg&#43;xml" data-processable="false" data-width="0" data-height="0" data-full-src="/manual/media/content-primitives-static.svg"',
            '<img src="/manual/media/content-primitives-static.svg" alt="Static SVG">',
            'data-kind="remote" data-media-type="image/png" data-processable="false" data-width="0" data-height="0" data-full-src="https://example.invalid/remote.png?fixture=1"',
            '<img src="https://example.invalid/remote.png?fixture=1" alt="Remote raster">',
        ):
            require(marker in compact_page, f"resolver matrix missing {marker}", errors)
    return errors


def check_image_hook_matrix(hugo: str) -> list[str]:
    """render-image: block vs inline, title, caption, num, dimensions, print, RSS."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-media-hook-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs/hook"
        layouts = temp_path / "layouts/docs"
        content.mkdir(parents=True)
        layouts.mkdir(parents=True)
        shutil.copyfile(PAGE_IMAGE, content / "page.png")
        (content / "index.md").write_text(
            "---\ntitle: Image hook\noutputs: [HTML, markdown, RSS, print]\n---\n\n"
            "## Block image (page resource)\n\n"
            '![Page raster](page.png "Advisory title")\n\n'
            "## Inline image\n\n"
            "Text with ![inline raster](page.png) inside a sentence.\n\n"
            "## Global asset and static file\n\n"
            "![Global raster](media/content-primitives-global.png)\n\n"
            "![Static SVG](/media/content-primitives-static.svg)\n\n"
            "## Remote\n\n"
            "![Remote raster](https://example.invalid/remote.png?fixture=1)\n\n"
            '![Quoted URL](https://example.invalid/image.svg?x="data-injected="yes&copy;=1)\n\n'
            'Inline ![Inline quoted URL](https://example.invalid/image.svg?x="data-injected="yes&copy;=1) image.\n\n'
            "## Caption figure and site class\n\n"
            "![Captioned](page.png)\n"
            '{caption="A plain caption" .wide data-fixture="figure"}\n\n'
            "## Numbered Book figure with explicit dimensions\n\n"
            "![Numbered](/media/content-primitives-static.svg)\n"
            '{#fig_static num="2-1" caption="Static with dimensions" width=640 height=480}\n\n'
            "## Numbered figure with default id and no caption\n\n"
            "![Numbered two](page.png)\n"
            '{num="2-2"}\n\n'
            'See {{< xref fig="2-1" anchor="fig_static" />}} and {{< xref fig="2-2" />}}.\n\n'
            "## Linked image\n\n"
            "[![Linked](page.png)](/docs/)\n"
        )
        # A scoped render (like content/rss-description.html) re-runs the hooks with the RSS store flag.
        (layouts / "single.rss.xml").write_text('{{- .Store.Set "tdOutputFormat" "rss" -}}\n<fixture>{{ (.Markup "td-rss-check").Render.Content }}</fixture>\n')
        override = temp_path / "rss.yaml"
        override.write_text("disableKinds: [sitemap, taxonomy, term]\noutputs:\n  home: [HTML]\n  section: [HTML]\n  page: [HTML, markdown, RSS, print]\n")
        destination = temp_path / "public"
        result = run_hugo(hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"), "--layoutDir", str(temp_path / "layouts"), "--destination", str(destination), "--config", fixture_media_config(override), "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"image hook matrix failed to build: {result.stdout}{result.stderr}")
            return errors
        html = (destination / "docs/hook/index.html").read_text()
        markdown = (destination / "docs/hook/index.md").read_text()
        print_html = (destination / "_print/docs/hook/index.html").read_text()
        rss_outputs = [path for path in destination.rglob("*.xml") if "hook" in path.parts]
        rss = rss_outputs[0].read_text() if rss_outputs else ""
        class ImageAttributes(HTMLParser):
            def __init__(self):
                super().__init__()
                self.images = {}

            def handle_starttag(self, tag, attrs):
                if tag == "img":
                    values = dict(attrs)
                    self.images[values.get("alt")] = values

        for output_name, output in (("HTML", html), ("Print", print_html), ("RSS", rss)):
            parsed = ImageAttributes()
            parsed.feed(output)
            for alt in ("Quoted URL", "Inline quoted URL"):
                attrs = parsed.images.get(alt, {})
                require(attrs.get("src") == 'https://example.invalid/image.svg?x="data-injected="yes&copy;=1',
                        f"{output_name}: image URL was truncated or entity-decoded", errors)
                require("data-injected" not in attrs,
                        f"{output_name}: image URL injected an HTML attribute", errors)
        for marker in (
            '<img class="td-image" src="/docs/hook/page.png" alt="Page raster" title="Advisory title" width="64" height="40" data-td-image-zoom loading="lazy" decoding="async">',
            'Text with <img src="/docs/hook/page.png" alt="inline raster" width="64" height="40" loading="lazy" decoding="async"> inside a sentence.',
            '<img class="td-image" src="/media/content-primitives-global.png" alt="Global raster" width="64" height="40" data-td-image-zoom loading="lazy" decoding="async">',
            '<img class="td-image" src="/media/content-primitives-static.svg" alt="Static SVG" data-td-image-zoom loading="lazy" decoding="async">',
            '<img class="td-image" src="https://example.invalid/remote.png?fixture=1" alt="Remote raster" data-td-image-zoom loading="lazy" decoding="async">',
            '<figure class="td-figure wide" data-fixture="figure">',
            '<figcaption> <span class="td-fig-caption">A plain caption</span></figcaption>',
            '<figure id="fig_static" class="td-figure td-book-figure td-book-figure--fig" data-td-book-kind="fig" data-td-book-num="2-1">',
            '<img src="/media/content-primitives-static.svg" alt="Numbered" width="640" height="480" data-td-image-zoom loading="lazy" decoding="async">',
            '<figcaption><span class="td-fig-label">Figure 2-1</span> <span class="td-fig-caption">Static with dimensions</span></figcaption>',
            '<figure id="fig-2-2" class="td-figure td-book-figure td-book-figure--fig" data-td-book-kind="fig" data-td-book-num="2-2">',
            '<figcaption><span class="td-fig-label">Figure 2-2</span></figcaption>',
            'href="#fig_static"',
            'href="#fig-2-2"',
            '<p><a href="/docs/"><img class="td-image" src="/docs/hook/page.png" alt="Linked" width="64" height="40" data-td-image-zoom loading="lazy" decoding="async"></a></p>',
        ):
            require(marker in html, f"image hook matrix HTML missing {marker}", errors)
        require("data-zoom-src" not in html, "the render-image hook emitted imgproc-only attributes", errors)
        require("<p><img" not in html and "<p class=\"td-image\">" not in html, "plain block images are wrapped in a paragraph again", errors)
        require(html.count('<figure class="td-figure') + html.count('<figure id="fig') == 3, "image hook matrix rendered a wrong number of figures", errors)
        for marker in ('![Page raster](page.png "Advisory title")', "![inline raster](page.png)", '{caption="A plain caption" .wide data-fixture="figure"}', '{#fig_static num="2-1" caption="Static with dimensions" width=640 height=480}'):
            require(marker in markdown, f"image hook matrix Markdown missing {marker}", errors)
        require("<img" not in markdown and "<figure" not in markdown, "image hook matrix Markdown contains HTML", errors)
        require(rss_outputs, "image hook matrix produced no RSS output", errors)
        if rss:
            require('src="https://example.org/docs/hook/page.png"' in rss, "RSS image src is not absolute", errors)
            require('src="https://example.org/media/content-primitives-static.svg"' in rss, "RSS static image src is not absolute", errors)
            require("Figure 2-1" in rss and "Static with dimensions" in rss, "RSS lost the numbered figure caption", errors)
    return errors


def check_subpath(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-media-subpath-") as temp:
        destination = Path(temp) / "public"
        result = run_hugo(hugo, "--source", str(FIXTURE), "--destination", str(destination), "--baseURL", "https://example.org/manual/", "--config", fixture_config(), "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"media subpath fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        page = (destination / "fixtures/media-primitives/index.html").read_text()
        for marker in (
            'src="/manual/fixtures/media-primitives/page_',
            'data-td-image-zoom="/manual/fixtures/media-primitives/page.png"',
            'src="/manual/media/content-primitives-global_',
            'data-td-image-zoom="/manual/media/content-primitives-global.png"',
            '<img class="td-image" src="/manual/fixtures/media-primitives/page.png" alt="Blue and gold page-resource test pattern" title="Advisory title"',
            '<img src="/manual/media/content-primitives-static.svg" alt="Static preview"',
        ):
            require(marker in page, f"media subpath fixture missing {marker}", errors)
    return errors


def check_rss_output(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-media-rss-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs/rss"
        layouts = temp_path / "layouts/docs"
        content.mkdir(parents=True)
        layouts.mkdir(parents=True)
        shutil.copyfile(PAGE_IMAGE, content / "page.png")
        (content / "index.md").write_text(
            "---\ntitle: RSS media\noutputs: [RSS]\n---\n\n"
            '![RSS image](page.png)\n{command="Fit" options="48x32" caption="RSS caption"}\n'
        )
        (layouts / "single.rss.xml").write_text('{{- .Store.Set "tdOutputFormat" "rss" -}}\n<fixture>{{ .RenderShortcodes }}</fixture>\n')
        override = temp_path / "rss.yaml"
        override.write_text("disableKinds: [sitemap, taxonomy, term]\noutputs:\n  home: [HTML]\n  section: [HTML]\n  page: [RSS]\n")
        destination = temp_path / "public"
        result = run_hugo(hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"), "--layoutDir", str(temp_path / "layouts"), "--destination", str(destination), "--config", f"{FIXTURE / 'hugo.yaml'},{override}", "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"RSS media fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        outputs = [path for path in destination.rglob("*.xml") if "rss" in path.parts]
        if not outputs:
            errors.append("RSS media fixture did not produce XML")
            return errors
        source = outputs[0].read_text()
        # This layout renders `.RenderShortcodes`, which expands shortcodes but
        # does not run render hooks. Every image form is a hook now, so the
        # output is the page source — the same reason Markdown output is source.
        for marker in ("![RSS image](page.png)", "RSS caption"):
            require(marker in source, f"RSS media fixture missing {marker}", errors)
        require("<figure" not in source, "RenderShortcodes rendered a hook it should not run", errors)
        for marker in ("<dialog", "td-image-zoom", "data-td-image-zoom", "data-zoom-src"):
            require(marker not in source, f"RSS media fixture contains Zoom marker {marker}", errors)
    return errors


def check_generic_rss_output(hugo: str) -> list[str]:
    """Guard HTML-first shortcode caches in Hugo's ordinary section feeds."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-media-generic-rss-") as temp:
        site = Path(temp)
        content = site / "content/docs/item"
        content.mkdir(parents=True)
        shutil.copyfile(PAGE_IMAGE, content / "page.png")
        (site / "content/docs/_index.md").write_text("---\ntitle: Docs\n---\n")
        (content / "index.md").write_text(
            "---\ntitle: RSS item\ndate: 2026-08-11\noutputs: [HTML, markdown]\n---\n\n"
            "Before image.\n\n"
            '![RSS generic image](page.png)\n{command="Fit" options="48x32" caption="Generic RSS caption"}\n\n'
            "![Hook image](page.png)\n"
        )
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\ntitle: RSS cache fixture\n"
            f"theme: {ROOT.name}\n"
            "disableKinds: [sitemap, taxonomy, term]\noutputs:\n  home: [HTML, RSS]\n  section: [HTML, RSS]\n  page: [HTML, markdown]\n"
            # The native image forms need the documented site prerequisites.
            "markup:\n  goldmark:\n    renderer:\n      unsafe: true\n"
            "    parser:\n      wrapStandAloneImageWithinParagraph: false\n      attribute:\n        block: true\n"
        )
        destination = site / "public"
        result = run_hugo(hugo, "--source", str(site), "--themesDir", str(ROOT.parent), "--destination", str(destination), "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"generic RSS media fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        output = destination / "docs/index.xml"
        if not output.exists():
            errors.append("generic RSS media fixture did not produce docs/index.xml")
            return errors
        source = output.read_text()
        # The section feed renders .Summary, which does run hooks: the figure is
        # real HTML (escaped into the feed) and the caption is plain text.
        for marker in ("Before image.", "&lt;figure", "RSS generic image", "Generic RSS caption", "Hook image"):
            require(marker in source, f"generic RSS media fixture missing {marker}", errors)
        for marker in ("![RSS generic image]", "data-zoom-src", "data-no-zoom", "data-td-image-zoom", "td-image-zoom", "<dialog"):
            require(marker not in source, f"generic RSS media fixture contains {marker}", errors)
    return errors


# The `image` shortcode is retired; its invalid cases moved to the hook below.
INVALID_CASES: tuple[tuple[str, str, str], ...] = ()


HOOK_INVALID_CASES = (
    ("hook-unknown-attr", '![x](page.png)\n{bogus="1"}\n', "unknown attribute"),
    ("hook-style", '![x](page.png)\n{style="width:10px"}\n', "unsafe attribute"),
    ("hook-width", '![x](page.png)\n{width="0"}\n', "width must be a positive integer"),
    ("hook-height", '![x](page.png)\n{height="abc"}\n', "height must be a positive integer"),
    ("hook-num", '![x](page.png)\n{num="1/2"}\n', "num must match"),
    ("hook-id", '![x](page.png)\n{#1bad num="1"}\n', "id must match"),
    ("hook-duplicate-num", '![x](page.png)\n{num="1"}\n\n![y](page.png)\n{num="1" #other}\n', "duplicate fig number"),
    ("hook-non-image", "![x](js/base.js)\n", "resolved to a non-image"),
    ("hook-unsafe-scheme", "![x](javascript:alert(1))\n", "unsupported src scheme"),
    ("hook-protocol-relative", "![x](//example.org/image.png)\n", "protocol-relative URL"),
    # `link` needs a figure to live in; the bare case already has native syntax.
    ("hook-link-without-caption", '![x](page.png)\n{link="/docs/"}\n', "link requires caption or num"),
    ("hook-link-unsafe", '![x](page.png)\n{caption="c" link="javascript:alert(1)"}\n', "unsupported link scheme"),
    # Processing on the attribute line reuses the shortcode's operation partial,
    # so it fails the same way on the same inputs.
    ("hook-command-without-options", '![x](page.png)\n{command="Fit"}\n', "command and options must be given together"),
    ("hook-options-without-command", '![x](page.png)\n{options="10x10"}\n', "command and options must be given together"),
    ("hook-command-unknown", '![x](page.png)\n{command="Squish" options="10x10"}\n', "command must be one of"),
    ("hook-command-on-static", '![x](/media/content-primitives-static.svg)\n{command="Fit" options="10x10"}\n', "cannot be processed"),
    # Video and audio share image syntax; their attributes warn the same way.
    ("hook-video-autoplay", '![x](https://example.org/clip.mp4)\n{autoplay="maybe"}\n', "autoplay must be true or false"),
    ("hook-video-width", '![x](https://example.org/clip.mp4)\n{width="0"}\n', "width must be a positive integer"),
    ("hook-video-link", '![x](https://example.org/clip.mp4)\n{link="/docs/"}\n', "unknown attribute"),
    ("hook-audio-unnamed", '![](https://example.org/tone.mp3)\n', "the bracket text names the recording"),
    ("hook-audio-unnamed-captioned", '![](https://example.org/tone.mp3)\n{caption="Voice note"}\n', "move the title from caption into the brackets"),
    ("hook-audio-invalid-id", '![x](https://example.org/tone.mp3)\n{#1bad}\n', "audio: id must match"),
    ("hook-audio-duplicate-id", '![x](https://example.org/tone.mp3)\n{#dup}\n\n![y](https://example.org/tone.mp3)\n{#dup}\n', 'audio: duplicate id "dup"'),
    ("hook-audio-preload-invalid", '![x](https://example.org/tone.mp3)\n{preload="auto"}\n', "audio: preload must be metadata or none"),
    ("hook-audio-num", '![x](https://example.org/tone.mp3)\n{num="1"}\n', "unknown attribute"),
    ("hook-audio-command", '![x](https://example.org/tone.mp3)\n{command="Fit" options="10x10"}\n', "unknown attribute"),
    ("hook-video-unnamed", '![](https://example.org/clip.mp4)\n', "the bracket text names the video"),
    ("hook-video-inline-unnamed", 'Watch ![](https://example.org/clip.mp4) now.\n', "the bracket text names the video"),
    ("hook-video-single-width", '![x](https://example.org/clip.mp4)\n{width="4"}\n', "width and height must be given together"),
    ("hook-platform-unnamed", '![](https://www.youtube.com/watch?v=dQw4w9WgXcQ)\n', "using the URL"),
    ("hook-audio-poster", '![x](https://example.org/tone.mp3)\n{poster="page.png"}\n', "unknown attribute"),
    ("hook-platform-no-id", '![x](https://www.youtube.com/watch?v=short)\n', "no YouTube video ID"),
    ("hook-platform-short-link", '![x](https://b23.tv/abc)\n', "short links cannot be resolved without the network"),
    ("hook-platform-autoplay", '![x](https://vimeo.com/76979871)\n{autoplay=true}\n', "unknown attribute"),
)


def check_invalid_cases(hugo: str) -> list[str]:
    errors: list[str] = []
    for name, body, expected in INVALID_CASES + HOOK_INVALID_CASES:
        with tempfile.TemporaryDirectory(prefix=f"oink-media-{name}-") as temp:
            temp_path = Path(temp)
            content = temp_path / "content/docs/invalid"
            content.mkdir(parents=True)
            shutil.copyfile(PAGE_IMAGE, content / "page.png")
            if "{{< image" in body:
                body = f"{body.rstrip()}{{{{< /image >}}}}\n"
            (content / "index.md").write_text(f"---\ntitle: Invalid media {name}\n---\n\n{body}")
            result = run_hugo(hugo, "--source", str(FIXTURE), "--contentDir", str(temp_path / "content"), "--destination", str(temp_path / "public"), "--logLevel", "warn")
            output = result.stdout + result.stderr
            if result.returncode != 0:
                errors.append(f"invalid media case {name} stopped the ordinary build instead of degrading: {output.strip()[-300:]}")
            if expected not in output:
                errors.append(f"invalid media case {name} did not report {expected!r}: {output.strip()}")
            if "content/docs/invalid/index.md:" not in output:
                errors.append(f"invalid media case {name} did not report its position")
            page = temp_path / "public/docs/invalid/index.html"
            if not page.is_file():
                errors.append(f"invalid media case {name} emitted no safe page output")
    return errors


def check_invalid_resource_alt(hugo: str) -> list[str]:
    """Wrong metadata types warn without breaking an ordinary image render."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-media-alt-") as temp:
        site = Path(temp)
        bundle = site / "content/docs/image"
        bundle.mkdir(parents=True)
        shutil.copyfile(PAGE_IMAGE, bundle / "page.png")
        (site / "hugo.yaml").write_text(
            f"baseURL: https://example.org/\ntitle: Alt fixture\ntheme: {ROOT.name}\n"
            "disableKinds: [RSS, sitemap, taxonomy, term]\n")
        layouts = site / "layouts/docs"
        layouts.mkdir(parents=True)
        (layouts / "single.html").write_text("{{ .Content }}")
        for value in ("{bad: type}", "[bad, type]"):
            (bundle / "index.md").write_text(
                "---\ntitle: Image\nresources:\n  - src: page.png\n    params:\n"
                f"      alt: {value}\n---\n![Authored alt](page.png)\n")
            command = ("--source", str(site), "--themesDir", str(ROOT.parent),
                       "--destination", str(site / "public"), "--logLevel", "warn")
            result = run_hugo(hugo, *command)
            require(result.returncode == 0, f"invalid resource alt stopped ordinary build: {result.stdout}{result.stderr}", errors)
            require("image resource alt metadata must be a string" in result.stdout + result.stderr,
                    "invalid resource alt did not warn", errors)
            if result.returncode == 0:
                require('alt="Authored alt"' in (site / "public/docs/image/index.html").read_text(),
                        "invalid resource alt displaced the authored alt", errors)
    return errors


def check_audio_matrix(hugo: str) -> list[str]:
    """Audio: local resources (incl. an extensionless audio/* resource and an
    upper-case static extension), encoded fragments, ARIA IDs (incl.
    shortcodes), duplicate IDs against Book targets in both orders, preload
    threshold, JS gating, 4 outputs, and absolute URLs under a subpath baseURL."""
    errors: list[str] = []
    silent_wav = (
        b"RIFF" + struct.pack("<I", 36) + b"WAVE"
        + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 8000, 1, 8)
        + b"data" + struct.pack("<I", 0)
    )
    with tempfile.TemporaryDirectory(prefix="oink-audio-matrix-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs"
        assets = temp_path / "assets/audio"
        static = temp_path / "static/audio"
        layouts = temp_path / "layouts/docs"
        synthetic = content / "audio-bundle"
        for directory in (content / "audio-matrix", content / "single-audio", content / "pair-audio", content / "audio-video", synthetic, assets, static, layouts):
            directory.mkdir(parents=True)
        (content / "audio-matrix/sample.wav").write_bytes(silent_wav)
        (assets / "global.wav").write_bytes(silent_wav)
        (static / "static.ogg").write_bytes(b"OggS")
        (static / "UPPER.MP3").write_bytes(b"ID3")
        # Hugo defines no audio/* media types, so recordings are found by
        # extension; a site-defined audio/* type on an extensionless resource
        # must still be detected by its media type, not its file name.
        (synthetic / "_content.gotmpl").write_text(
            '{{ .AddPage (dict "kind" "page" "path" "bundle" "title" "Bundle audio" '
            '"params" (dict "outputs" (slice "HTML")) '
            '"content" (dict "mediaType" "text/markdown" "value" "![Synthetic voice](voice#t=1,2)\\n")) }}\n'
            '{{ .AddResource (dict "path" "bundle/voice" "content" (dict "mediaType" "audio/x-oink-test" "value" "synthetic-audio")) }}\n'
        )
        (layouts / "single.rss.xml").write_text('{{- .Store.Set "tdOutputFormat" "rss" -}}\n<fixture>{{ (.Markup "td-rss-audio").Render.Content }}</fixture>\n')
        (content / "audio-matrix/index.md").write_text(
            "---\ntitle: Audio matrix\noutputs: [HTML, markdown, RSS, print]\n---\n\n"
            "![Local WAV](sample.wav?v=2#t=2,5)\n"
            '{#dup-audio caption="Captured note"}\n\n'
            "> [!DETAILS]- Transcript: Local WAV\n"
            ">\n"
            "> Spoken line for the local recording.\n\n"
            "![Global WAV](audio/global.wav#t=10,20)\n"
            '{#dup-audio}\n\n'
            "![Static OGG](/audio/static.ogg)\n"
            '{#mix-id}\n\n'
            "![Remote four](https://example.org/audio/4.mp3)\n\n"
            "![Remote five](https://example.org/audio/5.mp3)\n\n"
            "![Remote six](https://example.org/audio/6.mp3)\n"
            '{preload="none"}\n\n'
            "![Remote seven](https://example.org/audio/7.mp3)\n\n"
            "![Remote eight](https://example.org/audio/8.mp3)\n"
            '{preload="metadata"}\n\n'
            "![Upper-case static](/audio/UPPER.MP3)\n\n"
            "![Encoded fragment](sample.wav#t=1%2C2%22)\n\n"
            "![Audio before a numbered image](https://example.org/audio/9.mp3)\n"
            '{#audio-first}\n\n'
            "![Numbered image after audio](/media/content-primitives-static.svg)\n"
            '{num="2" #audio-first caption="Reuses the audio id"}\n\n'
            "![Numbered image before audio](/media/content-primitives-static.svg)\n"
            '{num="3" #image-first caption="Claims the id first"}\n\n'
            "![Audio after a numbered image](https://example.org/audio/10.mp3)\n"
            '{#image-first}\n\n'
            "![Numbered video colliding with audio id](https://example.org/video/demo.mp4)\n"
            '{num="1" #mix-id}\n\n'
            '{{< tabs >}}\n'
            '{{< tab label="Sample" >}}\n'
            "![Tabbed audio](sample.wav)\n"
            '{caption="Inside a tab"}\n'
            '{{< /tab >}}\n'
            '{{< /tabs >}}\n\n'
            "Inline ![inline clip](sample.wav#t=1,2) mention.\n"
        )
        (content / "single-audio/index.md").write_text(
            "---\ntitle: Single audio\noutputs: [HTML]\n---\n\n"
            "![Solo clip](https://example.org/audio/solo.mp3)\n"
        )
        (content / "pair-audio/index.md").write_text(
            "---\ntitle: Pair audio\noutputs: [HTML]\n---\n\n"
            "![First clip](https://example.org/audio/1.mp3)\n\n"
            "![Second clip](https://example.org/audio/2.mp3)\n"
        )
        (content / "audio-video/index.md").write_text(
            "---\ntitle: Audio and video\noutputs: [HTML]\n---\n\n"
            "![Voice](https://example.org/audio/1.mp3)\n\n"
            "![Clip](https://example.org/video/1.mp4)\n"
        )
        override = temp_path / "audio.yaml"
        override.write_text(
            "disableKinds: [sitemap, taxonomy, term]\n"
            "outputs:\n  home: [HTML]\n  section: [HTML]\n  page: [HTML, markdown, RSS, print]\n"
            "mediaTypes:\n  audio/x-oink-test:\n    suffixes: [oinkaudio]\n"
            f"assetDir: {temp_path / 'assets'}\n"
            f"staticDir:\n  - {FIXTURE / 'static'}\n  - {temp_path / 'static'}\n"
        )
        destination = temp_path / "public"
        result = run_hugo(
            hugo,
            "--source", str(FIXTURE),
            "--contentDir", str(temp_path / "content"),
            "--layoutDir", str(temp_path / "layouts"),
            "--destination", str(destination),
            "--config", fixture_media_config(override),
            "--logLevel", "warn",
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            errors.append(f"audio matrix failed to build: {output}")
            return errors

        require('audio: duplicate id "dup-audio"' in output, "audio matrix did not warn on duplicate audio id", errors)
        require('video: duplicate id "mix-id"' in output, "audio matrix did not warn when numbered video reused an audio id", errors)
        require('book component: duplicate id "audio-first"' in output and "already used by an unnumbered audio or video figure" in output,
                "a numbered image reusing an earlier audio id did not warn", errors)
        require('audio: duplicate id "image-first"' in output, "an audio reusing an earlier numbered image id did not warn", errors)
        require(output.count("audio: preload must be metadata or none") == 0, "valid preload values warned", errors)

        html = (destination / "docs/audio-matrix/index.html").read_text()
        print_html = (destination / "_print/docs/audio-matrix/index.html").read_text()
        markdown = (destination / "docs/audio-matrix/index.md").read_text()
        rss_outputs = [path for path in destination.rglob("*.xml") if "audio-matrix" in path.parts]
        rss = rss_outputs[0].read_text() if rss_outputs else ""

        class AudioParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.ids: dict[str, int] = {}
                self.audios: list[dict[str, str]] = []
                self.audio_figures: list[dict[str, str]] = []

            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                ident = values.get("id")
                if ident:
                    self.ids[ident] = self.ids.get(ident, 0) + 1
                if tag == "audio":
                    self.audios.append(values)
                if tag == "figure" and "td-media--audio" in (values.get("class") or "").split():
                    self.audio_figures.append(values)

        parsed = AudioParser()
        parsed.feed(html)
        for ident, count in parsed.ids.items():
            require(count == 1, f"audio matrix HTML has duplicate id {ident!r} ({count}x)", errors)
        require(len(parsed.audios) == 13, f"expected 13 <audio> players (12 main + 1 tab), got {len(parsed.audios)}", errors)
        for figure in parsed.audio_figures:
            classes = (figure.get("class") or "").split()
            require("td-figure" not in classes, "audio figure must not carry .td-figure", errors)
        require(html.count('id="dup-audio"') == 1, "duplicate audio id was not dropped on the second figure", errors)
        require(html.count('id="mix-id"') == 1, "colliding video id was not dropped after audio id", errors)

        by_src = {a.get("src", ""): a for a in parsed.audios}
        local_audio = by_src.get("/docs/audio-matrix/sample.wav?v=2#t=2,5")
        require(local_audio is not None, "local bundle audio lost query or #t= fragment", errors)
        if local_audio:
            require("aria-label" not in local_audio, "audio player should use aria-labelledby instead of aria-label", errors)
            lbl = local_audio.get("aria-labelledby", "")
            desc = local_audio.get("aria-describedby", "")
            require(lbl in parsed.ids, f"audio aria-labelledby {lbl!r} does not resolve", errors)
            require(desc in parsed.ids, f"audio aria-describedby {desc!r} does not resolve", errors)
            require(local_audio.get("preload") == "metadata", "first audio should default to preload=metadata", errors)
        require("/audio/global.wav#t=10,20" in by_src, "global audio resource lost #t= fragment", errors)
        require("/audio/static.ogg" in by_src, "static audio file did not render", errors)
        require(by_src.get("https://example.org/audio/5.mp3", {}).get("preload") == "metadata", "5th audio should default to preload=metadata", errors)
        require(by_src.get("https://example.org/audio/6.mp3", {}).get("preload") == "none", "explicit preload=none was ignored", errors)
        require(by_src.get("https://example.org/audio/7.mp3", {}).get("preload") == "none", "7th audio should auto-switch to preload=none", errors)
        require(by_src.get("https://example.org/audio/8.mp3", {}).get("preload") == "metadata", "explicit preload=metadata must override the 6-audio threshold", errors)
        require("/audio/UPPER.MP3" in by_src, "an upper-case audio extension was not detected", errors)
        require("/docs/audio-matrix/sample.wav#t=1%2C2%22" in by_src, "a percent-encoded fragment was decoded or lost on a local resource", errors)
        require('href="/docs/audio-matrix/sample.wav#t=1%2C2%22"' in html and "#t=1,2&#34;" not in html,
                "the screen URL line decoded the authored fragment", errors)
        require(html.count('id="audio-first"') == 1 and html.count('id="image-first"') == 1,
                "a duplicate id shared by audio and a numbered image survived", errors)
        bundle_html = (destination / "docs/audio-bundle/bundle/index.html").read_text()
        require('src="/docs/audio-bundle/bundle/voice#t=1,2"' in bundle_html and "<audio" in bundle_html,
                "an extensionless audio/* resource did not render as an audio player", errors)

        # Tabbed audio must have its generated title/caption IDs rewritten cleanly.
        tab_audio = by_src.get("/docs/audio-matrix/sample.wav")
        require(tab_audio is not None, "tabbed audio player missing", errors)
        if tab_audio:
            lbl = tab_audio.get("aria-labelledby", "")
            desc = tab_audio.get("aria-describedby", "")
            require(lbl.startswith("td-") and not lbl.startswith("td-audio-") and lbl in parsed.ids,
                    f"tabbed audio aria-labelledby was not scope-rewritten: {lbl!r}", errors)
            require(desc.startswith("td-") and not desc.startswith("td-audio-") and desc in parsed.ids,
                    f"tabbed audio aria-describedby was not scope-rewritten: {desc!r}", errors)

        require('<a class="td-media-link" href="/docs/audio-matrix/sample.wav#t=1,2">inline clip</a>' in html,
                "inline audio link lost its local fragment or class", errors)

        # Runtime gating: 1 audio loads 0 media JS; 2+ players load media chunk.
        single_html = (destination / "docs/single-audio/index.html").read_text()
        pair_html = (destination / "docs/pair-audio/index.html").read_text()
        av_html = (destination / "docs/audio-video/index.html").read_text()
        require("/js/chunks/media" not in single_html, "single-audio page unexpectedly loaded media.js", errors)
        require("/js/chunks/media" in pair_html, "two-audio page did not load media.js for single-active playback", errors)
        require("/js/chunks/media" in av_html, "audio+video page did not load media.js for single-active playback", errors)

        # Print output: visible .td-media__link (not .td-media__url), no <audio>, expanded transcript.
        require('<p class="td-media__link"><a href="/docs/audio-matrix/sample.wav?v=2#t=2,5">https://example.org/docs/audio-matrix/sample.wav?v=2#t=2,5</a></p>' in print_html,
                "print audio output missing visible td-media__link", errors)
        require("td-media__url" not in print_html, "print audio output still uses screen-hidden td-media__url", errors)
        require("<audio" not in print_html, "print output leaked <audio>", errors)
        require("Spoken line for the local recording." in print_html and "<details" not in print_html,
                "print output did not statically expand the transcript callout", errors)

        # RSS output: title links directly to absolute URL; no extra url paragraph.
        require(bool(rss_outputs), "audio matrix produced no RSS output", errors)
        if rss:
            require('<span class="td-media__title"><a href="https://example.org/docs/audio-matrix/sample.wav?v=2#t=2,5">Local WAV</a></span> <span class="td-fig-caption">Captured note</span>' in rss,
                    "RSS audio title is not linked directly to the absolute URL", errors)
            require("td-media__url" not in rss and "<audio" not in rss, "RSS audio output leaked player or td-media__url", errors)

        # Markdown output: authored syntax preserved, zero component HTML.
        require("![Local WAV](sample.wav?v=2#t=2,5)" in markdown, "Markdown output lost authored audio link", errors)
        require("> [!DETAILS]- Transcript: Local WAV" in markdown, "Markdown output lost transcript callout source", errors)
        require("<audio" not in markdown and "td-media" not in markdown, "Markdown output leaked audio HTML", errors)

        # A subpath baseURL: printed URLs keep the path for bundle and static files.
        subpath = temp_path / "public-subpath"
        result = run_hugo(
            hugo,
            "--source", str(FIXTURE),
            "--contentDir", str(temp_path / "content"),
            "--layoutDir", str(temp_path / "layouts"),
            "--destination", str(subpath),
            "--config", fixture_media_config(override),
            "--baseURL", "https://example.org/manual/",
            "--logLevel", "warn",
        )
        if result.returncode != 0:
            errors.append(f"audio matrix (subpath baseURL) failed to build: {result.stdout + result.stderr}")
            return errors
        sub_print = (subpath / "_print/docs/audio-matrix/index.html").read_text()
        require('<a href="/manual/docs/audio-matrix/sample.wav?v=2#t=2,5">https://example.org/manual/docs/audio-matrix/sample.wav?v=2#t=2,5</a>' in sub_print,
                "subpath print lost the baseURL path on a bundle recording", errors)
        require('<a href="/manual/audio/static.ogg">https://example.org/manual/audio/static.ogg</a>' in sub_print,
                "subpath print lost the baseURL path on a static recording", errors)
    return errors


def check_video_matrix(hugo: str) -> list[str]:
    """Video: media-type detection without binaries, leading-zero timestamps,
    platform URL variants, Shorts default ratio, poster vs aspect ratio, track
    query lookup, Print/RSS watch URLs, and Draw.io poster exclusion."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-video-matrix-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs/video-matrix"
        synthetic = temp_path / "content/docs/video-bundle"
        poster_only = temp_path / "content/docs/video-poster-only"
        layouts = temp_path / "layouts/docs"
        content.mkdir(parents=True)
        synthetic.mkdir(parents=True)
        poster_only.mkdir(parents=True)
        layouts.mkdir(parents=True)
        shutil.copyfile(PAGE_IMAGE, content / "page.png")
        shutil.copyfile(PAGE_IMAGE, poster_only / "page.png")
        (content / "sub.vtt").write_text("WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n")
        # Zero-binary synthetic video/mp4 page resource with a non-video extension
        # proves Hugo media-type detection runs before extension matching.
        (synthetic / "_content.gotmpl").write_text(
            '{{ .AddPage (dict "kind" "page" "path" "bundle" "title" "Bundle video" '
            '"params" (dict "outputs" (slice "HTML" "markdown" "RSS" "print")) '
            '"content" (dict "mediaType" "text/markdown" "value" '
            '"![Synthetic stream](stream.bin#t=2,4)\\n{poster=\\"page.png\\" track=\\"sub.vtt?v=2\\" width=\\"4\\" height=\\"3\\" caption=\\"Bundle clip\\"}\\n\\n'
            '![Remote track clip](stream.bin)\\n{track=\\"https://cdn.example.org/sub.vtt\\"}\\n\\n'
            '![Partial ratio](stream.bin)\\n{poster=\\"page.png\\" width=\\"4\\"}\\n")) }}\n'
            '{{ .AddResource (dict "path" "bundle/stream.bin" "content" (dict "mediaType" "video/mp4" "value" "synthetic-mp4")) }}\n'
            '{{ .AddResource (dict "path" "bundle/page.png" "content" (dict "mediaType" "image/png" "value" (resources.Get "media/content-primitives-global.png").Content)) }}\n'
            '{{ .AddResource (dict "path" "bundle/sub.vtt" "content" (dict "mediaType" "text/plain" "value" "WEBVTT\\n\\n00:00.000 --> 00:01.000\\nHello\\n")) }}\n'
        )
        (content / "index.md").write_text(
            "---\ntitle: Video matrix\noutputs: [HTML, markdown, RSS, print]\n---\n\n"
            "![YT leading zero](https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=08s)\n\n"
            "![YT short link slash](https://youtu.be/dQw4w9WgXcQ/?t=01m09s)\n\n"
            "![YT nocookie embed](https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?start=09)\n\n"
            "![YT music](https://music.youtube.com/watch?v=dQw4w9WgXcQ)\n\n"
            "![YT shorts vertical](https://www.youtube.com/shorts/dQw4w9WgXcQ)\n\n"
            "![Bili uppercase AV octal](https://www.bilibili.com/video/AV170001?t=010)\n\n"
            "![Bili b23 BV](https://b23.tv/BV1xx411c7mD)\n\n"
            "![Bili embed code](https://player.bilibili.com/player.html?isOutside=true&aid=170001&bvid=BV1xx411c7mD&cid=42&p=2&t=08)\n\n"
            "![Bili part fallback](https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&cid=unknown&p=2&t=08)\n\n"
            "![Bili embed aid](https://player.bilibili.com/player.html?aid=170002)\n\n"
            "![Vimeo query hash and fragment](https://vimeo.com/76979871?h=ABCDEF1234#t=01m08s)\n"
            '{poster="page.png" width="4" height="3" caption="Vimeo with poster and 4:3"}\n\n'
            "![Vimeo manage](https://vimeo.com/manage/videos/76979871)\n\n"
            "![Vimeo player host](https://player.vimeo.com/video/76979871?h=abcdef1234)\n\n"
            "![](https://www.youtube.com/watch?v=dQw4w9WgXcQ)\n"
        )
        (poster_only / "index.md").write_text(
            "---\ntitle: Poster only\n---\n\n"
            "![Card with PNG poster](https://www.bilibili.com/video/BV1xx411c7mD)\n"
            '{poster="page.png"}\n'
        )
        (layouts / "single.rss.xml").write_text(
            '{{- .Store.Set "tdOutputFormat" "rss" -}}\n<fixture>{{ (.Markup "td-rss-check").Render.Content }}</fixture>\n'
        )
        override = temp_path / "video.yaml"
        override.write_text(
            "disableKinds: [sitemap, taxonomy, term]\n"
            "outputs:\n  home: [HTML]\n  section: [HTML]\n  page: [HTML, markdown, RSS, print]\n"
            "params:\n"
            "  video_embeds: [youtube, bilibili, vimeo]\n"
            "  drawio:\n    enable: true\n    drawio_server: https://embed.diagrams.net/\n"
        )
        destination = temp_path / "public"
        result = run_hugo(
            hugo,
            "--source", str(FIXTURE),
            "--contentDir", str(temp_path / "content"),
            "--layoutDir", str(temp_path / "layouts"),
            "--destination", str(destination),
            "--config", fixture_media_config(override),
            "--logLevel", "warn",
        )
        output = result.stdout + result.stderr
        if result.returncode != 0:
            errors.append(f"video matrix failed to build: {output}")
            return errors

        require("width and height must be given together" in output,
                "video matrix did not warn on single width dimension", errors)
        require("using the URL" in output,
                "empty platform card did not warn about falling back to URL", errors)

        html = (destination / "docs/video-matrix/index.html").read_text()
        print_html = (destination / "_print/docs/video-matrix/index.html").read_text()
        rss_outputs = [path for path in destination.rglob("*.xml") if "video-matrix" in path.parts and "bundle" not in path.parts]
        rss = rss_outputs[0].read_text() if rss_outputs else ""

        for expected in (
            'data-td-media-embed="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1&amp;start=8"',
            'data-td-media-embed="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1&amp;start=69"',
            'data-td-media-embed="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1&amp;start=9"',
            'data-td-media-embed="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1"',
            'style="--td-media-ratio: 9 / 16" data-td-media-embed="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ?autoplay=1"',
            'data-td-media-embed="https://player.bilibili.com/player.html?aid=170001&amp;p=1&amp;autoplay=1&amp;danmaku=0&amp;t=10"',
            'data-td-media-embed="https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&amp;p=1&amp;autoplay=1&amp;danmaku=0"',
            # Bilibili's embed code: the BV ID wins over aid. A valid cid selects the part, otherwise p does.
            'data-td-media-embed="https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&amp;cid=42&amp;autoplay=1&amp;danmaku=0&amp;t=8"',
            'data-td-media-embed="https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&amp;p=2&amp;autoplay=1&amp;danmaku=0&amp;t=8"',
            'data-td-media-embed="https://player.bilibili.com/player.html?aid=170002&amp;p=1&amp;autoplay=1&amp;danmaku=0"',
            'data-td-media-embed="https://player.vimeo.com/video/76979871?autoplay=1&amp;dnt=1&amp;h=abcdef1234#t=68s"',
            'data-td-media-embed="https://player.vimeo.com/video/76979871?autoplay=1&amp;dnt=1"',
            'data-td-media-embed="https://player.vimeo.com/video/76979871?autoplay=1&amp;dnt=1&amp;h=abcdef1234"',
            '<span class="td-media-card__title">https://www.youtube.com/watch?v=dQw4w9WgXcQ</span>',
            '<span class="visually-hidden"> · </span>',
            '<p class="td-media__url"><span class="td-media__url-title">',
            # Poster <img> keeps its own 64x40 dimensions even with width="4" height="3".
            '<img class="td-media-card__poster" src="/docs/video-matrix/page.png" alt="" width="64" height="40"',
        ):
            require(expected in html, f"video matrix HTML missing {expected}", errors)
        require('<span class="td-media-card__title">watch</span>' not in html,
                "empty YouTube watch URL still fell back to 'watch'", errors)

        # Print and RSS platform cards carry visible watch URLs and preserve poster dimensions.
        for label, body in (("Print", print_html), ("RSS", rss)):
            require(bool(body), f"video matrix produced no {label} output", errors)
            require('<span class="td-media__address">https://vimeo.com/76979871?h=ABCDEF1234#t=01m08s</span>' in body,
                    f"video matrix {label} missing visible platform watch URL", errors)
            require('width="64" height="40"' in body and 'width="4" height="3"' not in body,
                    f"video matrix {label} clobbered poster image dimensions with aspect ratio", errors)

        # Synthetic zero-binary bundle resource: media-type detection, #t= fragment,
        # track query lookup, and single-dimension fallback.
        bundle_html = (destination / "docs/video-bundle/bundle/index.html").read_text()
        bundle_print = (destination / "_print/docs/video-bundle/bundle/index.html").read_text()
        for expected in (
            'src="/docs/video-bundle/bundle/stream.bin#t=2,4"',
            'style="aspect-ratio: 4 / 3"',
            '<track kind="subtitles" src="/docs/video-bundle/bundle/sub.vtt?v=2"',
            'src="/docs/video-bundle/bundle/stream.bin" crossorigin="anonymous"',
            '<track kind="subtitles" src="https://cdn.example.org/sub.vtt"',
            'style="aspect-ratio: 64 / 40"',
        ):
            require(expected in bundle_html, f"bundle video HTML missing {expected}", errors)
        require('src="/docs/video-bundle/bundle/stream.bin#t=2,4" crossorigin="anonymous"' not in bundle_html,
                "local video track unexpectedly emitted crossorigin=anonymous", errors)
        require('width="64" height="40"' in bundle_print and 'width="4" height="3"' not in bundle_print,
                "bundle video Print clobbered poster dimensions with aspect ratio", errors)

        # Draw.io must ignore PNG posters inside video cards.
        poster_only_html = (destination / "docs/video-poster-only/index.html").read_text()
        require('id="td-drawio-config"' not in poster_only_html and "drawioframe" not in combined_source(destination, poster_only_html),
                "Draw.io runtime loaded for a video card PNG poster", errors)
    return errors


def check_template_contracts() -> list[str]:
    errors: list[str] = []
    resolver = (ROOT / "layouts/_partials/content/image-resolve.html").read_text()
    processor = (ROOT / "layouts/_partials/content/image-process.html").read_text()
    hook = (ROOT / "layouts/_markup/render-image.html").read_text()
    require("resources.GetRemote" not in resolver + processor + hook, "media layer fetches remote images", errors)
    # One lookup order for images and media: the image resolver and the media
    # partials both delegate to content/resource-lookup.html.
    lookup = (ROOT / "layouts/_partials/content/resource-lookup.html").read_text()
    media = (ROOT / "layouts/_partials/content/media.html").read_text()
    detect = (ROOT / "layouts/_partials/content/media-detect.html").read_text()
    require('partial "content/resource-lookup.html"' in resolver, "image resolver does not use the shared resource lookup", errors)
    require('partial "content/resource-lookup.html"' in detect + media, "media partials do not use the shared resource lookup", errors)
    require("$page.Resources.Get" in lookup, "resource lookup lacks exact page resources", errors)
    require("resources.Get $lookup" in lookup, "resource lookup lacks global resources", errors)
    require(lookup.index("$page.Resources.Get") < lookup.index("resources.Get $lookup"), "resource lookup order is not page then global", errors)
    require("resources.GetRemote" not in lookup + media + detect, "media layer fetches remote media", errors)
    require('partial "content/media-detect.html"' in hook and 'partial "content/media.html"' in hook, "render-image.html does not dispatch media", errors)
    require('partial "content/url.html"' in media, "media sources skip the shared URL policy", errors)
    # The mechanical answer -- URL, dimensions, media type, processability --
    # lives in the shared media-result contract; the resolver must consume it
    # rather than re-deriving its own, and the contract must keep the guards.
    media_contract = (ROOT / "layouts/_partials/_funcs/media-result.html").read_text()
    require('partial "_funcs/media-result.html"' in resolver, "resolver does not consume the shared media contract", errors)
    require("reflect.IsImageResourceProcessable" in media_contract, "media contract does not test processability", errors)
    require("reflect.IsImageResourceWithMeta" in media_contract, "media contract does not guard dimensions", errors)
    landing_media = (ROOT / "layouts/_partials/landing/media-resolve.html").read_text()
    featured = (ROOT / "layouts/_partials/featured-image-resolve.html").read_text()
    for name, source in (("landing", landing_media), ("featured", featured)):
        require('partial "_funcs/media-result.html"' in source,
                f"{name} resolver does not speak the shared media contract", errors)
    require("resources.GetRemote" not in media_contract + landing_media, "media contract fetches remote images", errors)
    require("try ($image.resource.Fit" in processor, "image operations are not guarded", errors)
    # The `image` shortcode is retired: the attribute line carries processing,
    # numbering, linking and captions, and the render hook owns all of them.
    require(not (ROOT / "layouts/_shortcodes/image.html").exists(), "image.html must stay deleted", errors)
    require("data-zoom-src" not in hook, "the render hook emits the retired data-zoom-src attribute", errors)
    for marker in ('partial "content/image-process.html"', '"command"', '"options"', '"link"', "td-figure__byline", 'partial "content/image-resolve.html"', 'partial "content/attributes.html"', ".IsBlock", '"width" "height"', 'partial "book/register-target.html"', 'loading="lazy" decoding="async"', "absURL", "td-figure", "td-image", ".Title"):
        require(marker in hook, f"render-image.html lacks {marker}", errors)
    require(not (ROOT / "layouts/_shortcodes/imgproc.html").exists(), "imgproc.html must stay deleted", errors)
    static_output = 'partial "content/static-image-output.html"'
    rss_description = 'partial "content/rss-description.html"'
    for relative in ("layouts/_partials/content/rss.html", "layouts/blog/rss.xml"):
        require(rss_description in (ROOT / relative).read_text(), f"{relative} does not use the shared RSS description renderer", errors)
    for relative in ("layouts/_default/rss.xml", "layouts/landing.rss.xml"):
        require('partial "content/rss.html"' in (ROOT / relative).read_text(),
                f"{relative} does not use the shared RSS document renderer", errors)
    require(static_output in (ROOT / "layouts/_partials/content/rss-description.html").read_text(), "RSS description renderer does not remove interaction-only image attributes", errors)
    # Every print aggregate renders page content through one cached partial,
    # which is where the static-image filter runs.
    require(static_output in (ROOT / "layouts/_partials/print/page-content.html").read_text(), "print/page-content.html does not remove interaction-only image attributes", errors)
    for relative in ("layouts/_partials/print/content.html", "layouts/_partials/print/render.html", "layouts/_partials/book/print.html", "layouts/docs/single.print.html", "layouts/blog/single.print.html", "layouts/book/single.print.html"):
        source = (ROOT / relative).read_text()
        require('partialCached "print/page-content.html"' in source and "RenderString" not in source, f"{relative} must render page content through the cached print/page-content.html partial", errors)
    return errors


def check_media_stylesheet() -> list[str]:
    """Card geometry and paper colors that Chromium-only browser runs miss:
    WebKit neither narrows a clamped aspect-ratio box nor grows one for a
    wrapped title, and a dark screen palette must not reach paper."""
    errors: list[str] = []
    css = (ROOT / "assets/css/td/media.css").read_text()
    runtime = (ROOT / "assets/js/media.js").read_text()
    cap = "max-inline-size: min(100%, calc(80vh * var(--td-media-ratio, 16 / 9)));"
    require(css.count(cap) == 2, "media.css must cap card and player width by --td-media-ratio", errors)
    require(css.count("aspect-ratio: var(--td-media-ratio, 16 / 9);") == 2,
            "media.css card and player must take their ratio from --td-media-ratio", errors)
    for selector in (".td-media-card {", ".td-media-player {"):
        start = css.find("\n" + selector)
        body = css[start:css.find("}", start)] if start != -1 else ""
        require(bool(body) and "max-block-size" not in body,
                f"media.css {selector[:-2]} clamps its ratio box by height, which WebKit does not transfer to its width", errors)
    supports = css.find("@supports (min-block-size: 1cqi)")
    require(supports != -1
            and "container-type: inline-size;" in css[supports:]
            and "min-block-size: min(calc(100cqi / (var(--td-media-ratio, 16 / 9))), 80vh);" in css[supports:],
            "media.css lacks the container-unit minimum height that lets a long title grow the card", errors)
    paper = css.find("@media print")
    require(paper != -1 and ".td-media-card:not(:has(.td-media-card__poster)) .td-media-card__text" in css[paper:],
            "media.css print colors do not reach the poster-less card text", errors)
    require("getPropertyValue('--td-media-ratio')" in runtime and "setProperty('--td-media-ratio'" in runtime,
            "media.js does not carry the card ratio to the player", errors)
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
        + check_resolver_matrix(args.hugo)
        + check_image_hook_matrix(args.hugo)
        + check_subpath(args.hugo)
        + check_rss_output(args.hugo)
        + check_generic_rss_output(args.hugo)
        + check_invalid_cases(args.hugo)
        + check_invalid_resource_alt(args.hugo)
        + check_audio_matrix(args.hugo)
        + check_video_matrix(args.hugo)
        + check_template_contracts()
        + check_media_stylesheet()
    )
    if errors:
        print("Media primitive checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Media primitive checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
