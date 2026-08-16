#!/usr/bin/env python3
"""Validate shared image resolution, the render-image hook, and the image shortcode."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
PAGE_IMAGE = EXAMPLE / "content/docs/media-primitives/page.png"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def run_hugo(hugo: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([hugo, *args], cwd=ROOT, capture_output=True, text=True, check=False)


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    page = (public / "docs/media-primitives/index.html").read_text()
    markdown = (public / "docs/media-primitives/index.md").read_text()
    print_page = (public / "_print/docs/index.html").read_text()

    for marker in (
        # image shortcode: processed figure with a Markdown caption
        '<figure class="td-figure td-figure--processed" style="max-width: 50px">',
        'data-zoom-src="/docs/media-primitives/page.png"',
        'alt="Blue and gold page-resource test pattern" width="48" height="30"',
        'data-zoom-src="/media/content-primitives-global.png"',
        'alt="Green and violet global-resource test pattern" width="32" height="20"',
        'data-no-zoom alt="" width="24" height="24"',
        'alt="Page resource metadata alternative" width="40" height="24"',
        "<figcaption><p>A <strong>page resource</strong> caption with <code>inline code</code>.</p>",
        '<small class="td-figure__byline">OINK fixture byline</small>',
        # render-image hook: plain block image is a bare block-level img with the zoom marker; title stays advisory
        '<img class="td-image" src="/docs/media-primitives/page.png" alt="Blue and gold page-resource test pattern" title="Advisory title" width="64" height="40" data-td-image-zoom loading="lazy" decoding="async">',
        # render-image hook: block image + {caption=} becomes a figure
        '<figure class="td-figure">',
        '<img src="/media/content-primitives-static.svg" alt="Static preview" loading="lazy" decoding="async">',
        '<figcaption> <span class="td-fig-caption">A static image with a caption becomes a figure</span></figcaption>',
    ):
        require(marker in page, f"HTML media fixture missing {marker}", errors)
    require(page.count("td-figure--processed") == 4, "image shortcode lost a fixture", errors)
    require(page.count('loading="lazy" decoding="async"') == 6, "images lack stable loading attributes", errors)
    require("td-imgproc" not in page and "card-img-top" not in page, "legacy imgproc markup survived", errors)
    require("resources.GetRemote" not in page, "rendered media output leaked template code", errors)

    for marker in (
        "![Blue and gold page\\-resource test pattern](/docs/media-primitives/page_",
        "![Green and violet global\\-resource test pattern](/media/content-primitives-global_",
        "![](/docs/media-primitives/page_",
        "![Page resource metadata alternative](/docs/media-primitives/page_",
        "A **page resource** caption with `inline code`.",
        "_OINK fixture byline_",
        # hook-rendered images keep their source Markdown (RenderShortcodes does not run hooks)
        '![Blue and gold page-resource test pattern](page.png "Advisory title")',
        "![Static preview](/media/content-primitives-static.svg)",
        '{caption="A static image with a caption becomes a figure"}',
    ):
        require(marker in markdown, f"Markdown media fixture missing {marker}", errors)
    for marker in ("<figure", "<img", "td-figure", "data-zoom-src"):
        require(marker not in markdown, f"Markdown media output contains {marker}", errors)
    require(markdown.count("![") == 6, "Markdown media output lost image order", errors)

    for marker in (
        "Blue and gold page-resource test pattern",
        "Green and violet global-resource test pattern",
        "Page resource metadata alternative",
        "page_hu_",
        "content-primitives-global_hu_",
        "OINK fixture byline",
        '<figure class="td-figure">',
        "A static image with a caption becomes a figure",
    ):
        require(marker in print_page, f"print media fixture missing {marker}", errors)
    require("data-zoom-src" not in print_page and "data-td-image-zoom" not in print_page, "print media output kept interactive zoom attributes", errors)
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
        result = run_hugo(hugo, "--source", str(EXAMPLE), "--contentDir", str(temp_path / "content"), "--layoutDir", str(temp_path / "layouts"), "--destination", str(destination), "--baseURL", "https://example.org/manual/", "--logLevel", "warn")
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
    """render-image: block vs inline, title, caption, num, width/height, rss."""
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="oink-media-hook-") as temp:
        temp_path = Path(temp)
        content = temp_path / "content/docs/hook"
        layouts = temp_path / "layouts/docs"
        content.mkdir(parents=True)
        layouts.mkdir(parents=True)
        shutil.copyfile(PAGE_IMAGE, content / "page.png")
        (content / "index.md").write_text(
            "---\ntitle: Image hook\noutputs: [HTML, markdown, RSS]\n---\n\n"
            "## Block image (page resource)\n\n"
            '![Page raster](page.png "Advisory title")\n\n'
            "## Inline image\n\n"
            "Text with ![inline raster](page.png) inside a sentence.\n\n"
            "## Global asset and static file\n\n"
            "![Global raster](media/content-primitives-global.png)\n\n"
            "![Static SVG](/media/content-primitives-static.svg)\n\n"
            "## Remote\n\n"
            "![Remote raster](https://example.invalid/remote.png?fixture=1)\n\n"
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
        override.write_text("disableKinds: [sitemap, taxonomy, term]\noutputs:\n  home: [HTML]\n  section: [HTML]\n  page: [HTML, markdown, RSS]\n")
        destination = temp_path / "public"
        result = run_hugo(hugo, "--source", str(EXAMPLE), "--contentDir", str(temp_path / "content"), "--layoutDir", str(temp_path / "layouts"), "--destination", str(destination), "--config", f"{EXAMPLE / 'hugo.yaml'},{override}", "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"image hook matrix failed to build: {result.stdout}{result.stderr}")
            return errors
        html = (destination / "docs/hook/index.html").read_text()
        markdown = (destination / "docs/hook/index.md").read_text()
        rss_outputs = [path for path in destination.rglob("*.xml") if "hook" in path.parts]
        rss = rss_outputs[0].read_text() if rss_outputs else ""
        for marker in (
            '<img class="td-image" src="/docs/hook/page.png" alt="Page raster" title="Advisory title" width="64" height="40" data-td-image-zoom loading="lazy" decoding="async">',
            'Text with <img src="/docs/hook/page.png" alt="inline raster" width="64" height="40" loading="lazy" decoding="async"> inside a sentence.',
            '<img class="td-image" src="/media/content-primitives-global.png" alt="Global raster" width="64" height="40" data-td-image-zoom loading="lazy" decoding="async">',
            '<img class="td-image" src="/media/content-primitives-static.svg" alt="Static SVG" data-td-image-zoom loading="lazy" decoding="async">',
            '<img class="td-image" src="https://example.invalid/remote.png?fixture=1" alt="Remote raster" data-td-image-zoom loading="lazy" decoding="async">',
            '<figure class="td-figure wide" data-fixture="figure">',
            '<figcaption> <span class="td-fig-caption">A plain caption</span></figcaption>',
            '<figure id="fig_static" class="td-figure td-book-figure td-book-figure--fig" data-book-kind="fig" data-book-num="2-1">',
            '<img src="/media/content-primitives-static.svg" alt="Numbered" width="640" height="480" loading="lazy" decoding="async">',
            '<figcaption><span class="td-fig-label">Figure 2-1</span> <span class="td-fig-caption">Static with dimensions</span></figcaption>',
            '<figure id="fig-2-2" class="td-figure td-book-figure td-book-figure--fig" data-book-kind="fig" data-book-num="2-2">',
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
        result = run_hugo(hugo, "--source", str(EXAMPLE), "--destination", str(destination), "--baseURL", "https://example.org/manual/", "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"media subpath fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        page = (destination / "docs/media-primitives/index.html").read_text()
        for marker in (
            'src="/manual/docs/media-primitives/page_',
            'data-zoom-src="/manual/docs/media-primitives/page.png"',
            'src="/manual/media/content-primitives-global_',
            'data-zoom-src="/manual/media/content-primitives-global.png"',
            '<img class="td-image" src="/manual/docs/media-primitives/page.png" alt="Blue and gold page-resource test pattern" title="Advisory title"',
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
            '{{< image src="page.png" command="Fit" options="48x32" alt="RSS image" >}}\n'
            "Static **RSS caption**.\n"
            "{{< /image >}}\n"
        )
        (layouts / "single.rss.xml").write_text('{{- .Store.Set "tdOutputFormat" "rss" -}}\n<fixture>{{ .RenderShortcodes }}</fixture>\n')
        override = temp_path / "rss.yaml"
        override.write_text("disableKinds: [sitemap, taxonomy, term]\noutputs:\n  home: [HTML]\n  section: [HTML]\n  page: [RSS]\n")
        destination = temp_path / "public"
        result = run_hugo(hugo, "--source", str(EXAMPLE), "--contentDir", str(temp_path / "content"), "--layoutDir", str(temp_path / "layouts"), "--destination", str(destination), "--config", f"{EXAMPLE / 'hugo.yaml'},{override}", "--logLevel", "warn")
        if result.returncode != 0:
            errors.append(f"RSS media fixture failed to build: {result.stdout}{result.stderr}")
            return errors
        outputs = [path for path in destination.rglob("*.xml") if "rss" in path.parts]
        if not outputs:
            errors.append("RSS media fixture did not produce XML")
            return errors
        source = outputs[0].read_text()
        for marker in ('<figure class="td-figure td-figure--processed"', 'alt="RSS image" width="48" height="30"', "<strong>RSS caption</strong>"):
            require(marker in source, f"RSS media fixture missing {marker}", errors)
        require("![RSS image]" not in source, "RSS used Markdown image fallback", errors)
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
            '{{< image src="page.png" command="Fit" options="48x32" alt="RSS generic image" >}}\n'
            "Generic **RSS caption**.\n"
            "{{< /image >}}\n\n"
            "![Hook image](page.png)\n"
        )
        (site / "hugo.yaml").write_text(
            "baseURL: https://example.org/\ntitle: RSS cache fixture\n"
            f"theme: {ROOT.name}\n"
            "disableKinds: [sitemap, taxonomy, term]\noutputs:\n  home: [HTML, RSS]\n  section: [HTML, RSS]\n  page: [HTML, markdown]\n"
            "markup:\n  goldmark:\n    renderer:\n      unsafe: true\n"
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
        for marker in ("Before image.", "&lt;figure", "RSS generic image", "&lt;strong&gt;RSS caption&lt;/strong&gt;", "Hook image"):
            require(marker in source, f"generic RSS media fixture missing {marker}", errors)
        for marker in ("![RSS generic image]", "data-zoom-src", "data-no-zoom", "data-td-image-zoom", "td-image-zoom", "<dialog"):
            require(marker not in source, f"generic RSS media fixture contains {marker}", errors)
    return errors


INVALID_CASES = (
    ("empty", "{{< image >}}\n", "requires named parameters"),
    ("positional", '{{< image "page.png" Fit "40x20" >}}\n', "requires named parameters"),
    ("missing-src", '{{< image command="Fit" options="40x20" alt="x" >}}\n', "requires parameter src"),
    ("empty-src", '{{< image src="" command="Fit" options="40x20" alt="x" >}}\n', "src must not be empty"),
    ("src-type", '{{< image src=true command="Fit" options="40x20" alt="x" >}}\n', "src must be a string"),
    ("missing-command", '{{< image src="page.png" options="40x20" alt="x" >}}\n', "requires parameter command"),
    ("command-type", '{{< image src="page.png" command=true options="40x20" alt="x" >}}\n', "command must be a string"),
    ("command-value", '{{< image src="page.png" command="Scale" options="40x20" alt="x" >}}\n', "command must be one of"),
    ("missing-options", '{{< image src="page.png" command="Fit" alt="x" >}}\n', "requires parameter options"),
    ("options-type", '{{< image src="page.png" command="Fit" options=true alt="x" >}}\n', "options must be a string"),
    ("options-empty", '{{< image src="page.png" command="Fit" options="" alt="x" >}}\n', "options must not be empty"),
    ("options-invalid", '{{< image src="page.png" command="Fit" options="nonsense" alt="x" >}}\n', "failed for src"),
    ("missing-alt", '{{< image src="page.png" command="Fit" options="40x20" >}}\n', "requires meaningful alt text or decorative=true"),
    ("empty-alt", '{{< image src="page.png" command="Fit" options="40x20" alt="" >}}\n', "requires meaningful alt text or decorative=true"),
    ("alt-type", '{{< image src="page.png" command="Fit" options="40x20" alt=true >}}\n', "alt must be a string"),
    ("decorative-type", '{{< image src="page.png" command="Fit" options="40x20" decorative="true" >}}\n', "decorative must be boolean"),
    ("decorative-alt", '{{< image src="page.png" command="Fit" options="40x20" decorative=true alt="x" >}}\n', "decorative images must not define alt text"),
    ("unknown", '{{< image src="page.png" command="Fit" options="40x20" alt="x" loading="eager" >}}\n', "unsupported parameter"),
    ("missing-resource", '{{< image src="missing.png" command="Fit" options="40x20" alt="x" >}}\n', "cannot be processed"),
    ("static-resource", '{{< image src="/media/content-primitives-static.svg" command="Fit" options="40x20" alt="x" >}}\n', "cannot be processed"),
    ("remote-resource", '{{< image src="https://example.invalid/image.png" command="Fit" options="40x20" alt="x" >}}\n', "cannot be processed"),
    ("svg-resource", '{{< image src="media/content-primitives-global.svg" command="Fit" options="40x20" alt="x" >}}\n', "cannot be processed"),
    ("non-image", '{{< image src="js/base.js" command="Fit" options="40x20" alt="x" >}}\n', "resolved to a non-image"),
    ("unsafe-scheme", '{{< image src="javascript:alert(1)" command="Fit" options="40x20" alt="x" >}}\n', "unsupported src scheme"),
    ("protocol-relative", '{{< image src="//example.org/image.png" command="Fit" options="40x20" alt="x" >}}\n', "protocol-relative URL"),
    ("source-space", '{{< image src="/bad path.png" command="Fit" options="40x20" alt="x" >}}\n', "whitespace or control characters"),
)

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
            result = run_hugo(hugo, "--source", str(EXAMPLE), "--contentDir", str(temp_path / "content"), "--destination", str(temp_path / "public"), "--logLevel", "warn")
            output = result.stdout + result.stderr
            if result.returncode == 0:
                errors.append(f"invalid media case {name} unexpectedly built")
            else:
                if expected not in output:
                    errors.append(f"invalid media case {name} did not report {expected!r}: {output.strip()}")
                if "content/docs/invalid/index.md:" not in output:
                    errors.append(f"invalid media case {name} did not report its position")
    return errors


def check_template_contracts() -> list[str]:
    errors: list[str] = []
    resolver = (ROOT / "layouts/_partials/content/image-resolve.html").read_text()
    processor = (ROOT / "layouts/_partials/content/image-process.html").read_text()
    image = (ROOT / "layouts/_shortcodes/image.html").read_text()
    hook = (ROOT / "layouts/_markup/render-image.html").read_text()
    require("resources.GetRemote" not in resolver + processor + image + hook, "media layer fetches remote images", errors)
    require("$page.Resources.Get" in resolver, "resolver lacks exact page resources", errors)
    require("resources.Get $lookup" in resolver, "resolver lacks global resources", errors)
    require(resolver.index("$page.Resources.Get") < resolver.index("resources.Get $lookup"), "resolver order is not page then global", errors)
    require("reflect.IsImageResourceProcessable" in resolver, "resolver does not test processability", errors)
    require("reflect.IsImageResourceWithMeta" in resolver, "resolver does not guard dimensions", errors)
    require("try ($image.resource.Fit" in processor, "image operations are not guarded", errors)
    require("requires named parameters" in image and ".IsNamedParams" in image, "image shortcode is not named-only", errors)
    require('"requireAlt" true' in image, "image shortcode does not require alt or decorative", errors)
    require('eq $format "markdown"' in image, "image shortcode lacks Markdown output", errors)
    require("Page.Store.Set" not in image, "image shortcode sets a runtime flag", errors)
    require("data-zoom-src" in image, "image shortcode does not expose its canonical source", errors)
    require("render-block.html" in image, "image shortcode caption is not rendered in a scoped RenderString", errors)
    for marker in ('partial "content/image-resolve.html"', 'partial "content/attributes.html"', ".IsBlock", '"width" "height"', 'partial "book/register-target.html"', "wrapStandAloneImageWithinParagraph", 'loading="lazy" decoding="async"', "absURL", "td-figure", "td-image", ".Title"):
        require(marker in hook, f"render-image.html lacks {marker}", errors)
    require(not (ROOT / "layouts/_shortcodes/imgproc.html").exists(), "imgproc.html must stay deleted", errors)
    static_output = 'partial "content/static-image-output.html"'
    rss_description = 'partial "content/rss-description.html"'
    for relative in ("layouts/_default/rss.xml", "layouts/blog/rss.xml"):
        require(rss_description in (ROOT / relative).read_text(), f"{relative} does not use the shared RSS description renderer", errors)
    require(static_output in (ROOT / "layouts/_partials/content/rss-description.html").read_text(), "RSS description renderer does not remove interaction-only image attributes", errors)
    for relative in ("layouts/_partials/print/content.html", "layouts/_partials/print/render.html"):
        require(static_output in (ROOT / relative).read_text(), f"{relative} does not remove interaction-only image attributes", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, default=EXAMPLE / "public")
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    errors = (
        check_outputs(args.public)
        + check_resolver_matrix(args.hugo)
        + check_image_hook_matrix(args.hugo)
        + check_subpath(args.hugo)
        + check_rss_output(args.hugo)
        + check_generic_rss_output(args.hugo)
        + check_invalid_cases(args.hugo)
        + check_template_contracts()
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
