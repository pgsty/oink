#!/usr/bin/env python3
"""Validate shared image resolution and the render-image hook (all image forms)."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
PAGE_IMAGE = EXAMPLE / "content/fixtures/media-primitives/page.png"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def run_hugo(hugo: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([hugo, *args], cwd=ROOT, capture_output=True, text=True, check=False)


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    page = (public / "fixtures/media-primitives/index.html").read_text()
    markdown = (public / "fixtures/media-primitives/index.md").read_text()
    print_page = (public / "_print/fixtures/index.html").read_text()

    for marker in (
        # attribute line + {command=/options=}: processed figure, Zoom marker
        # carrying the full-size original
        '<figure class="td-figure">',
        '<img src="/fixtures/media-primitives/page_hu_9fe7555f90baf6dd.png" alt="Blue and gold page-resource test pattern" width="48" height="30" data-td-image-zoom="/fixtures/media-primitives/page.png" loading="lazy" decoding="async">',
        '<img src="/media/content-primitives-global_hu_aaa8925533bfdda.png" alt="Green and violet global-resource test pattern" width="32" height="20" data-td-image-zoom="/media/content-primitives-global.png" loading="lazy" decoding="async">',
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
    # Hugo's image-processing cache key changed between supported releases for
    # Crop. Assert the generated-resource shape and semantics, not one Hugo
    # version's opaque hash.
    require(
        re.search(
            r'<img class="td-image" src="/fixtures/media-primitives/page_hu_[0-9a-f]+\.png" alt="" width="24" height="24" loading="lazy" decoding="async">',
            page,
        )
        is not None,
        "HTML media fixture lacks the decorative processed image",
        errors,
    )
    # The retired shortcode owned this class; nothing emits it any more.
    require("td-figure--processed" not in page, "the retired processed-figure class survived", errors)
    # The byline belongs to the resource, so every captioned figure built from
    # that resource carries it — the behaviour the retired shortcode had.
    require(page.count("td-figure__byline") == 4, "the resource byline is not rendered on every figure of that resource", errors)
    require(page.count('loading="lazy" decoding="async"') == 8, "images lack stable loading attributes", errors)
    require("td-imgproc" not in page and "card-img-top" not in page, "legacy imgproc markup survived", errors)
    require("resources.GetRemote" not in page, "rendered media output leaked template code", errors)

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
        result = run_hugo(hugo, "--source", str(EXAMPLE), "--destination", str(destination), "--baseURL", "https://example.org/manual/", "--logLevel", "warn")
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
        result = run_hugo(hugo, "--source", str(EXAMPLE), "--contentDir", str(temp_path / "content"), "--layoutDir", str(temp_path / "layouts"), "--destination", str(destination), "--config", f"{EXAMPLE / 'hugo.yaml'},{override}", "--logLevel", "warn")
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
    hook = (ROOT / "layouts/_markup/render-image.html").read_text()
    require("resources.GetRemote" not in resolver + processor + hook, "media layer fetches remote images", errors)
    require("$page.Resources.Get" in resolver, "resolver lacks exact page resources", errors)
    require("resources.Get $lookup" in resolver, "resolver lacks global resources", errors)
    require(resolver.index("$page.Resources.Get") < resolver.index("resources.Get $lookup"), "resolver order is not page then global", errors)
    require("reflect.IsImageResourceProcessable" in resolver, "resolver does not test processability", errors)
    require("reflect.IsImageResourceWithMeta" in resolver, "resolver does not guard dimensions", errors)
    require("try ($image.resource.Fit" in processor, "image operations are not guarded", errors)
    # The `image` shortcode is retired: the attribute line carries processing,
    # numbering, linking and captions, and the render hook owns all of them.
    require(not (ROOT / "layouts/_shortcodes/image.html").exists(), "image.html must stay deleted", errors)
    require("data-zoom-src" not in hook, "the render hook emits the retired data-zoom-src attribute", errors)
    for marker in ('partial "content/image-process.html"', '"command"', '"options"', '"link"', "td-figure__byline", 'partial "content/image-resolve.html"', 'partial "content/attributes.html"', ".IsBlock", '"width" "height"', 'partial "book/register-target.html"', "wrapStandAloneImageWithinParagraph", 'loading="lazy" decoding="async"', "absURL", "td-figure", "td-image", ".Title"):
        require(marker in hook, f"render-image.html lacks {marker}", errors)
    require(not (ROOT / "layouts/_shortcodes/imgproc.html").exists(), "imgproc.html must stay deleted", errors)
    static_output = 'partial "content/static-image-output.html"'
    rss_description = 'partial "content/rss-description.html"'
    for relative in ("layouts/_default/rss.xml", "layouts/blog/rss.xml"):
        require(rss_description in (ROOT / relative).read_text(), f"{relative} does not use the shared RSS description renderer", errors)
    require(static_output in (ROOT / "layouts/_partials/content/rss-description.html").read_text(), "RSS description renderer does not remove interaction-only image attributes", errors)
    # Every print aggregate renders page content through one cached partial,
    # which is where the static-image filter runs.
    require(static_output in (ROOT / "layouts/_partials/print/page-content.html").read_text(), "print/page-content.html does not remove interaction-only image attributes", errors)
    for relative in ("layouts/_partials/print/content.html", "layouts/_partials/print/render.html", "layouts/_partials/book/print.html", "layouts/docs/single.print.html", "layouts/blog/single.print.html", "layouts/book/single.print.html"):
        source = (ROOT / relative).read_text()
        require('partialCached "print/page-content.html"' in source and "RenderString" not in source, f"{relative} must render page content through the cached print/page-content.html partial", errors)
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
