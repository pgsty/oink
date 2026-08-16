#!/usr/bin/env python3
"""Validate Image Zoom gating, output isolation, and runtime contracts."""

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


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def enclosing_selectors(styles: str, position: int) -> list[str]:
    """Return the selector text of every SCSS block that encloses ``position``."""
    selectors: list[str] = []
    depth = 0
    index = position
    while index > 0:
        index -= 1
        char = styles[index]
        if char == "}":
            depth += 1
        elif char == "{":
            if depth:
                depth -= 1
                continue
            start = max(styles.rfind("}", 0, index), styles.rfind("{", 0, index), styles.rfind(";", 0, index))
            selectors.append(styles[start + 1 : index].strip())
    return selectors


def run_hugo(hugo: str, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [hugo, *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def bundle_path(public: Path, page: str) -> tuple[Path | None, str]:
    source = (public / page).read_text()
    match = MAIN_SCRIPT.search(source)
    if not match:
        return None, source
    relative = unescape(match.group(1)).split("?", 1)[0].lstrip("/")
    return public / relative, source


def check_outputs(public: Path) -> list[str]:
    errors: list[str] = []
    zoom_path, zoom = bundle_path(public, "docs/image-zoom/index.html")
    disabled_path, disabled = bundle_path(public, "docs/image-zoom-disabled/index.html")
    excluded_path, excluded = bundle_path(public, "docs/image-zoom-exclusions/index.html")
    plain_path, plain = bundle_path(public, "docs/content-primitives/index.html")
    markdown = (public / "docs/image-zoom/index.md").read_text()
    print_page = (public / "_print/docs/index.html").read_text()
    media = (public / "docs/media-primitives/index.html").read_text()
    blog_path, blog = bundle_path(public, "blog/index.html")

    for marker in (
        'class="td-image-zoom d-print-none"',
        "data-td-image-zoom-dialog",
        'aria-label="Image preview"',
        'data-open-label="Open image preview"',
        "data-td-image-zoom-close",
        "data-td-image-zoom-image",
        "data-td-image-zoom-caption",
        "Blue and gold standalone preview",
        "Green and violet processed preview",
        'data-zoom-src="/media/content-primitives-global.png"',
        'data-zoom-src="/docs/image-zoom/legacy-empty.png" alt=""',
        "Linked image remains a link",
    ):
        require(marker in zoom, f"enabled Zoom fixture missing {marker}", errors)
    require(zoom.count("data-td-image-zoom-dialog") == 1, "enabled page emitted more than one dialog", errors)
    require(zoom_path is not None and zoom_path.exists(), "enabled page has no local main bundle", errors)
    if zoom_path and zoom_path.exists():
        zoom_bundle = zoom_path.read_text()
        require("data-td-image-zoom-dialog" in zoom_bundle, "enabled bundle omits Image Zoom", errors)
        require("HTMLDialogElement" in zoom_bundle, "enabled bundle lacks dialog feature detection", errors)

    for label, page, path in (
        ("page-disabled", disabled, disabled_path),
        ("excluded-only", excluded, excluded_path),
        ("candidate-free", plain, plain_path),
    ):
        require("data-td-image-zoom-dialog" not in page, f"{label} page emitted a dialog", errors)
        require(path is not None and path.exists(), f"{label} page has no main bundle", errors)
        if path and path.exists():
            require(
                "data-td-image-zoom-dialog" not in path.read_text(),
                f"{label} page loaded the Zoom runtime",
                errors,
            )

    require(zoom_path != disabled_path, "Zoom and non-Zoom pages reused one bundle target", errors)
    zoom_tag = MAIN_SCRIPT.search(zoom)
    require(zoom_tag is not None, "enabled page lacks its main script tag", errors)
    if zoom_tag:
        tag_end = zoom.find(">", zoom_tag.start())
        tag = zoom[zoom_tag.start() : tag_end + 1]
        require('integrity="sha256-' in tag, "Zoom bundle is not fingerprinted with SRI", errors)
        require("http://" not in tag and "https://" not in tag, "Zoom bundle is not local", errors)
    require(
        zoom.index("data-td-image-zoom-dialog") < zoom.index(zoom_tag.group(0)) if zoom_tag else False,
        "dialog is not present before the runtime executes",
        errors,
    )
    require(not re.search(r"\son[a-z]+\s*=", zoom, re.I), "Zoom markup contains an inline event handler", errors)

    for marker in ("<dialog", "td-image-zoom", "data-td-image-zoom", "data-zoom-src"):
        require(marker not in markdown, f"Markdown output contains Zoom marker {marker}", errors)
        require(marker not in print_page, f"print output contains Zoom marker {marker}", errors)
    require("![Blue and gold standalone preview]" in markdown, "Markdown lost the standalone image", errors)
    require("![](/docs/image-zoom/legacy-empty_" in markdown, "Markdown lost the legacy empty-alt image", errors)
    require("data-no-zoom" in media, "explicit decorative imgproc is not excluded from Zoom", errors)
    require("data-td-image-zoom-dialog" in blog, "blog content candidate did not request Zoom", errors)
    require("td-blog-posts-list__thumbnail" in blog, "blog scope fixture lacks a featured thumbnail", errors)
    require(blog_path is not None and blog_path.exists(), "blog scope fixture lacks a main bundle", errors)
    return errors


def site_config(value: str | None) -> str:
    config = (
        "baseURL: https://example.org/\n"
        "title: Zoom gate fixture\n"
        f"theme: {ROOT.name}\n"
        "disableKinds: [RSS, sitemap, taxonomy, term]\n"
        "markup:\n  goldmark:\n    renderer:\n      unsafe: true\n"
    )
    if value is not None:
        config += "params:\n  ui:\n    image_zoom:\n      enable: " + value + "\n"
    return config


def page_front_matter(value: str | None) -> str:
    front = "---\ntitle: Zoom gate\n"
    if value is not None:
        front += "params:\n  ui:\n    image_zoom:\n      enable: " + value + "\n"
    return front + "---\n\n"


def build_gate_case(
    hugo: str,
    *,
    site_value: str | None,
    page_value: str | None,
    body: str,
) -> tuple[subprocess.CompletedProcess[str], str]:
    with tempfile.TemporaryDirectory(prefix="oink-image-zoom-gate-") as temp:
        site = Path(temp)
        (site / "content/docs").mkdir(parents=True)
        (site / "static").mkdir()
        (site / "hugo.yaml").write_text(site_config(site_value))
        (site / "content/docs/index.md").write_text(page_front_matter(page_value) + body)
        (site / "static/image.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="40">'
            '<rect width="64" height="40" fill="#1677ff"/></svg>\n'
        )
        destination = site / "public"
        result = run_hugo(
            hugo,
            "--source",
            str(site),
            "--themesDir",
            str(ROOT.parent),
            "--destination",
            str(destination),
            "--logLevel",
            "warn",
        )
        page = ""
        output = destination / "docs/index.html"
        if result.returncode == 0 and output.exists():
            page = output.read_text()
        return result, page


def check_config_matrix(hugo: str) -> list[str]:
    errors: list[str] = []
    candidate = "![Gate candidate](/image.svg)\n"
    cases = (
        ("default-off", None, None, candidate, False),
        ("page-on", None, "true", candidate, True),
        ("site-on", "true", None, candidate, True),
        ("page-false-wins", "true", "false", candidate, False),
        ("no-candidate", "true", None, "No image here.\n", False),
    )
    for name, site_value, page_value, body, expected_zoom in cases:
        result, page = build_gate_case(
            hugo,
            site_value=site_value,
            page_value=page_value,
            body=body,
        )
        if result.returncode != 0:
            errors.append(f"Zoom config case {name} failed: {result.stdout}{result.stderr}")
            continue
        actual = "data-td-image-zoom-dialog" in page
        require(actual == expected_zoom, f"Zoom config case {name} resolved to {actual}", errors)

    invalid = (
        ("site-string", '"true"', None, "site parameter params.ui.image_zoom.enable must be a boolean"),
        ("site-number", "1", None, "site parameter params.ui.image_zoom.enable must be a boolean"),
        ("page-string", None, '"false"', "page parameter params.ui.image_zoom.enable must be a boolean"),
    )
    for name, site_value, page_value, expected in invalid:
        result, _ = build_gate_case(
            hugo,
            site_value=site_value,
            page_value=page_value,
            body="No image required.\n",
        )
        output = result.stdout + result.stderr
        require(result.returncode != 0, f"invalid Zoom config {name} unexpectedly built", errors)
        require(expected in output, f"invalid Zoom config {name} did not report its boolean path", errors)
        if name.startswith("page"):
            require("/docs" in output, "invalid page Zoom config omitted its page", errors)
    return errors


def check_candidate_exclusions(hugo: str) -> list[str]:
    errors: list[str] = []
    excluded_cases = (
        ("empty-alt", '<p><img src="/image.svg" alt=""></p>\n'),
        ("role-none", '<p><img src="/image.svg" alt="" role="none"></p>\n'),
        ("role-presentation-uppercase", '<p><img src="/image.svg" alt="Decorative" role="PRESENTATION"></p>\n'),
        ("aria-hidden-uppercase", '<p><img src="/image.svg" alt="Hidden" aria-hidden="TRUE"></p>\n'),
    )
    for name, body in excluded_cases:
        result, page = build_gate_case(
            hugo,
            site_value="true",
            page_value=None,
            body=body,
        )
        if result.returncode != 0:
            errors.append(f"Zoom exclusion case {name} failed: {result.stdout}{result.stderr}")
            continue
        raw_target = re.search(rf'<img\b[^>]*\bsrc="/image\.svg"[^>]*>', page)
        if not raw_target:
            errors.append(f"Zoom exclusion case {name} did not render its target image")
            continue
        require(
            "data-td-image-zoom-dialog" not in page,
            f"Zoom exclusion case {name} requested the runtime",
            errors,
        )

    result, page = build_gate_case(
        hugo,
        site_value="true",
        page_value=None,
        body='<p><img src="/image.svg" alt="Informative image"></p>\n',
    )
    if result.returncode != 0:
        errors.append(f"Zoom informative candidate failed: {result.stdout}{result.stderr}")
    else:
        require(
            "data-td-image-zoom-dialog" in page,
            "Zoom informative candidate did not request the runtime",
            errors,
        )
    return errors


def check_template_contracts() -> list[str]:
    errors: list[str] = []
    scripts = (ROOT / "layouts/_partials/scripts.html").read_text()
    config = (ROOT / "layouts/_partials/content/image-zoom-config.html").read_text()
    render = (ROOT / "layouts/_partials/content/render.html").read_text()
    candidate = (ROOT / "layouts/_partials/content/image-zoom-candidate.html").read_text()
    dialog = (ROOT / "layouts/_partials/content/image-zoom-dialog.html").read_text()
    runtime = (ROOT / "assets/js/image-zoom.js").read_text()
    styles = (ROOT / "assets/scss/td/shortcodes/content-primitives.scss").read_text()

    for path in (ROOT / "layouts").rglob("*.html"):
        relative = path.relative_to(ROOT).as_posix()
        if relative in {
            "layouts/_partials/content/render.html",
            "layouts/_partials/print/content.html",
            "layouts/_partials/print/render.html",
        }:
            continue
        require(
            not re.search(r"{{-?\s*(?:with\s+)?\.Content\b", path.read_text()),
            f"{relative} bypasses content/render.html",
            errors,
        )

    bundle = re.search(r'\$bundleKey := printf "([^"]+)"(.*?)\| md5', scripts, re.S)
    require(bundle is not None, "scripts.html bundle key is not inspectable", errors)
    if bundle:
        expression = re.sub(
            r'\(not\s+\(\.Param\s+"[^"]+"\)\)',
            " ARG ",
            bundle.group(2),
        )
        placeholders = len(re.findall(r"%(?:v|s)", bundle.group(1)))
        arguments = re.findall(r"\$[A-Za-z][A-Za-z0-9]*|\.[A-Za-z][A-Za-z0-9_.]*|\bARG\b", expression)
        require(placeholders == len(arguments), "bundle key format/argument count diverged", errors)
        require("$hasImageZoom" in bundle.group(2), "bundle key omits the Zoom variant", errors)

    require('resources.Get "js/image-zoom.js"' in scripts, "scripts.html does not append Zoom", errors)
    require('partial "content/image-zoom-dialog.html"' in scripts, "scripts.html does not emit the dialog", errors)
    require(scripts.index('partial "content/image-zoom-dialog.html"') < scripts.index("$js :="), "dialog renders after the bundle", errors)
    require('partial "content/image-zoom-candidate.html"' in render, "content renderer does not scan candidates", errors)
    require('.Store.Set "hasImageZoom" true' in render, "content renderer does not set the Page Store flag", errors)
    require(".Content" not in scripts, "scripts.html forces page content rendering", errors)
    require('printf "%T" $value' in config and '"bool"' in config, "Zoom config is not strict boolean", errors)
    require("data-no-zoom" in candidate and "standaloneParagraph" in candidate, "candidate scan lacks exclusions or structure", errors)
    require("<dialog" in dialog and "data-td-image-zoom-close" in dialog, "Zoom dialog lacks native markup", errors)
    require(not re.search(r"\son[a-z]+\s*=", dialog, re.I), "dialog partial contains inline handlers", errors)

    for marker in (
        "HTMLDialogElement",
        "showModal",
        "data-no-zoom",
        "dataset.zoomSrc",
        "currentSrc",
        "event.target === dialog",
        "backdropPressed",
        "origin.focus",
        "document.createElement('button')",
    ):
        require(marker in runtime, f"Zoom runtime lacks {marker}", errors)
    require("role === 'none'" in runtime, "Zoom runtime does not exclude role=none", errors)
    require("alt?.trim()" in runtime, "Zoom runtime does not exclude empty-alt images", errors)
    require("style.inlineSize" not in runtime, "Zoom runtime freezes trigger width in pixels", errors)
    for forbidden in ("eval(", "new Function", ".innerHTML"):
        require(forbidden not in runtime, f"Zoom runtime contains {forbidden}", errors)
    require("Open image preview" not in runtime, "Zoom runtime contains an unlocalized visible fallback", errors)
    require("#td-main-content img" not in runtime, "Zoom runtime scans theme chrome outside content", errors)
    for marker in ("forced-colors", "::backdrop", "@media print"):
        require(marker in styles, f"Zoom styles lack {marker}", errors)
    require(".td-image-zoom:not([open])" in styles, "Zoom lacks an unsupported-dialog closed fallback", errors)
    # Zoom itself must not animate. content-primitives.scss also hosts other
    # primitives, so scope the motion assertion to rule blocks whose selector
    # names the Zoom, and separately require a reduced-motion path for any
    # motion the rest of the file declares.
    for match in re.finditer(r"^\s*(?:transition|animation)\s*:", styles, re.M):
        selectors = " ".join(enclosing_selectors(styles, match.start()))
        require("td-image-zoom" not in selectors, "Zoom adds motion without a reduction path", errors)
    if re.search(r"^\s*(?:transition|animation)\s*:", styles, re.M):
        reduce_block = re.search(r"@media \(prefers-reduced-motion: reduce\)\s*\{(.*?)\n\}", styles, re.S)
        require(
            reduce_block is not None and "transition: none" in reduce_block.group(1),
            "content primitives declare motion without a prefers-reduced-motion path",
            errors,
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, default=EXAMPLE / "public")
    parser.add_argument("--hugo", default="hugo")
    args = parser.parse_args()

    errors = (
        check_outputs(args.public)
        + check_config_matrix(args.hugo)
        + check_candidate_exclusions(args.hugo)
        + check_template_contracts()
    )
    if errors:
        print("Image Zoom checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Image Zoom checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
