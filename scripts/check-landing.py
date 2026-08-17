#!/usr/bin/env python3
"""Validate the landing shell, sections, output matrix, and failures."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "exampleSite"
MAIN_SCRIPT = re.compile(r'<script src="(?P<src>/js/page-[^"]+\.js)"')


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(
    hugo: str, source: Path, destination: Path | None = None
) -> subprocess.CompletedProcess[str]:
    command = [hugo, "--source", str(source), "--logLevel", "warn"]
    if destination is not None:
        command.extend(["--destination", str(destination)])
    return subprocess.run(
        command, cwd=ROOT, capture_output=True, text=True, check=False
    )


def bundle_path(source: str) -> str:
    match = MAIN_SCRIPT.search(source)
    return match.group("src") if match else ""


def check_example(public: Path) -> list[str]:
    errors: list[str] = []
    paths = {
        "html": public / "landing-demo/index.html",
        "print": public / "_print/landing-demo/index.html",
        "markdown": public / "landing-demo/index.md",
        "docs": public / "docs/index.html",
    }
    for name, path in paths.items():
        require(path.exists(), f"landing {name} fixture is missing", errors)
    if not all(path.exists() for path in paths.values()):
        return errors

    html = paths["html"].read_text(encoding="utf-8")
    print_html = paths["print"].read_text(encoding="utf-8")
    markdown = paths["markdown"].read_text(encoding="utf-8")
    docs = paths["docs"].read_text(encoding="utf-8")

    for marker in (
        'class="td-site-header',
        'data-td-landing',
        'class="td-site-footer',
        'data-td-navbar-columns="2"',
        'data-td-github-stars>2.2k',
        'class="td-nav-util td-nav-alt-site"',
        'class="td-footer__copyright"',
        'class="td-shell-footline__center">Powered by <a href="https://oink.pgsty.com">Oink</a>',
        'data-td-shell-search-open',
        'data-td-theme-toggle',
        'data-td-landing-menu-toggle',
    ):
        require(marker in html, f"landing shell lost {marker}", errors)
    for marker in ('id="td-section-nav"', 'class="td-shell-sidebar', 'class="td-toc'):
        require(marker not in html, f"landing shell unexpectedly contains {marker}", errors)

    section_markers = (
        'class="td-landing-hero',
        '--td-hero-title-size: 4.25rem',
        'data-td-count="2189"',
        '>2.2k</strong>',
        'class="td-landing-metric__source"',
        'data-td-theme-src-light="/icons/logo.svg"',
        'data-td-theme-src-dark="/icons/logo.svg#dark"',
        'td-landing-faq-list--flat',
        'class="td-landing-pricing-tier td-landing-pricing-tier--featured"',
        'aria-label="Included"',
        'aria-label="Not included"',
        'class="td-landing-command-box"',
        '<pre tabindex="0"><code class="language-bash">',
        'class="td-landing-landing-steps"',
        'class="td-landing-timeline"',
        'class="highlight"><pre tabindex="0" class="chroma"',
        'class="td-landing-case-study"',
        'class="td-landing-download-tabs"',
        'class="td-landing-marquee__pause"',
        'data-td-marquee-pause',
        'class="nav nav-tabs" role="tablist"',
        '--td-bar-width: 100.0000%',
        '--td-bar-width: 3.8839%',
    )
    for marker in section_markers:
        require(marker in html, f"landing section fixture lost {marker}", errors)

    require(
        html.count('class="td-landing-marquee__group"') == 4,
        "two-row marquee did not render one original and one duplicate per row",
        errors,
    )
    require(
        html.count('class="td-landing-marquee__group" aria-hidden="true"') == 2,
        "marquee duplicates are not consistently hidden from accessibility APIs",
        errors,
    )
    require(
        html.count('class="td-landing-marquee__group" aria-hidden="true" inert') == 2,
        "marquee duplicates are not removed from sequential focus",
        errors,
    )

    landing_bundle = bundle_path(html)
    docs_bundle = bundle_path(docs)
    require(landing_bundle and docs_bundle, "landing or docs bundle is missing", errors)
    require(landing_bundle != docs_bundle, "hasLanding did not alter the bundle key", errors)
    if landing_bundle:
        source = (public / landing_bundle.lstrip("/")).read_text(encoding="utf-8")
        require("OinkLanding" in source, "landing runtime was not bundled", errors)
    if docs_bundle:
        source = (public / docs_bundle.lstrip("/")).read_text(encoding="utf-8")
        require("OinkLanding" not in source, "docs page bundled the landing runtime", errors)

    for marker in (
        "td-landing-marquee--static",
        "Static pricing cards",
        "curl -fsSL https://example.org/install | bash",
        "--td-bar-width: 3.8839%",
    ):
        require(marker in print_html, f"landing print output lost {marker}", errors)
    for marker in (
        "data-td-landing",
        "data-td-marquee",
        'aria-hidden="true"><article class="td-landing-logo-card"',
        "data-td-reveal",
        "data-td-count=",
        "data-td-copy-text",
        "data-theme-src",
        "OinkLanding",
    ):
        require(marker not in print_html, f"landing print output is interactive: {marker}", errors)

    for marker in (
        "## Any page can be a landing page",
        "[Read the docs](/docs/)",
        "- **2189** Stars",
        "[**PostgreSQL**](/docs/)",
        "[Documentation](/docs/)",
        "| Feature | Community | Professional |",
        "| --- | --- | --- |",
        "```yaml\nlayout: landing",
        "## Install script",
        "- Decimal value: 43.5 units",
    ):
        require(marker in markdown, f"landing Markdown lost {marker}", errors)
    for marker in ("%!s(<nil>)", "data-td-", "td-landing-", "<section", "<button"):
        require(marker not in markdown, f"landing Markdown leaked {marker}", errors)
    return errors


def check_sources() -> list[str]:
    errors: list[str] = []
    section = (ROOT / "layouts/_partials/landing/section.html").read_text()
    field = (ROOT / "layouts/_partials/landing/field.html").read_text()
    scripts = (ROOT / "layouts/_partials/scripts.html").read_text()
    navbar = (ROOT / "layouts/_partials/navbar.html").read_text()
    styles = (ROOT / "assets/scss/td/_landing.scss").read_text()
    runtime = (ROOT / "assets/js/landing.js").read_text()
    require(
        (ROOT / "layouts/baseof.landing.html").read_text()
        == (ROOT / "layouts/baseof.html").read_text(),
        "landing HTML base selector drifted from the shared base",
        errors,
    )
    require(
        (ROOT / "layouts/baseof.landing.print.html").read_text()
        == (ROOT / "layouts/baseof.print.html").read_text(),
        "landing print base selector drifted from the shared print base",
        errors,
    )

    registered = set(re.findall(r'"([a-z-]+)"\s+"landing/sections/', section))
    expected = {
        "hero", "metrics", "capabilities", "principles", "cards", "logo-wall",
        "gallery", "testimonials", "contributors", "faq", "markdown", "cta",
        "pricing", "pricing-compare", "command-box", "steps", "timeline",
        "code-plate", "case-study", "download", "bar-chart",
    }
    require(registered == expected, f"landing registry is {sorted(registered)}", errors)
    require('partial "landing/entry.html"' in section, "HTML dispatcher bypasses shared entry normalization", errors)
    require('printf "%s_%s" $key $lang' in field, "field helper lacks full language fallback", errors)
    require('printf "%s_%s" $key $primary' in field, "field helper lacks primary language fallback", errors)
    require("$hasLanding" in scripts and "js/landing.js" in scripts, "hasLanding assembly is incomplete", errors)
    require(
        '$landingSurface := eq .Layout "landing"' in navbar
        and '$landingSurface := or .IsHome' not in navbar,
        "Landing mobile menu escaped onto the homepage",
        errors,
    )
    require(
        "body:has([data-td-landing-menu-toggle])" in (
            ROOT / "assets/scss/td/_site-navbar.scss"
        ).read_text()
        and "body:has([data-td-landing])" not in (
            ROOT / "assets/scss/td/_site-navbar.scss"
        ).read_text(),
        "Landing compact navbar CSS is not keyed to its rendered menu toggle",
        errors,
    )
    for marker in (
        "@media (prefers-reduced-motion: reduce)",
        "@media (forced-colors: active)",
        "@media print",
        "[dir='rtl'] .td-landing-marquee",
        "&:has(&__pause input:checked) &__track",
    ):
        require(marker in styles, f"landing styles lack {marker}", errors)
    for marker in (
        "IntersectionObserver", "data-td-copy-text", "data-td-theme-src-light",
        "OinkSurfaceCoordinator", "register('mobile-menu'",
    ):
        require(marker in runtime, f"landing runtime lacks {marker}", errors)
    marquee = (ROOT / "layouts/_partials/landing/marquee.html").read_text()
    require('T "ui_marquee_pause"' in marquee, "marquee pause control is not localized", errors)
    require('aria-hidden="true" inert' in marquee, "marquee duplicate is not inert", errors)

    for name in ("cover", "feature", "lead", "link-down", "section"):
        require(not (ROOT / f"layouts/_shortcodes/blocks/{name}.html").exists(), f"blocks/{name} must stay deleted (v5 §1.1: layout: landing replaces the Docsy blocks)", errors)
    compatibility = {
        "action.html": "landing/action.html",
        "heading.html": "landing/heading.html",
        "markdown-block.html": "landing/markdown-block.html",
        "markdown.html": "landing/markdown.html",
        "media.html": "landing/media.html",
        "section.html": "landing/section.html",
        **{
            f"sections/{name}.html": f"landing/sections/{name}.html"
            for name in (
                "capabilities", "cards", "contributors", "cta", "faq",
                "gallery", "hero", "logo-wall", "markdown", "metrics",
                "principles", "testimonials",
            )
        },
    }
    home_root = ROOT / "layouts/_partials/home"
    actual = {
        str(path.relative_to(home_root))
        for path in home_root.rglob("*.html")
    }
    require(actual == set(compatibility), "legacy home adapter set drifted", errors)
    for name, target in compatibility.items():
        source = (home_root / name).read_text()
        require(
            "Deprecated compatibility adapter" in source
            and f'partial "{target}" .' in source
            and len(source.splitlines()) == 2,
            f"legacy adapter {name} is not a thin landing wrapper",
            errors,
        )
    home_data = (ROOT / "layouts/_partials/home-data.html").read_text()
    require(
        "Deprecated compatibility adapter" in home_data
        and 'partial "landing/home-data.html" .' in home_data
        and len(home_data.splitlines()) == 2,
        "legacy home-data adapter is not a thin landing wrapper",
        errors,
    )
    return errors


def create_site(root: Path, landing_data: str, *, language: str = "en") -> None:
    (root / "themes").mkdir(parents=True)
    (root / "themes/oink").symlink_to(ROOT, target_is_directory=True)
    write(
        root / "hugo.yaml",
        f"""baseURL: https://example.org/
title: Landing fixture
theme: oink
defaultContentLanguage: {language}
languages:
  {language}:
    label: Fixture
    weight: 1
disableKinds: [home, RSS, sitemap, taxonomy, term]
outputs:
  page: [HTML]
params:
  offline_search: false
  ui:
    pager_types: []
""",
    )
    write(
        root / "content/test.md",
        "---\ntitle: Test landing\ntype: docs\nlayout: landing\nlanding: demo\n---\n",
    )
    if landing_data:
        write(root / "data/landing/demo.yaml", landing_data)


INVALID_CASES = (
    ("missing-data", "", "was not found"),
    ("bad-visual", "sections:\n  - type: capabilities\n    data:\n      items:\n        - title: Bad\n          visual: {type: video}\n", "unsupported visual.type"),
    ("missing-alt", "sections:\n  - type: capabilities\n    data:\n      items:\n        - title: Bad\n          visual: {type: image, src: /bad.png}\n", "requires alt"),
    ("bad-faq", "sections:\n  - type: faq\n    data:\n      style: tabs\n      items: [{question: Q, answer: A}]\n", "faq.style must be accordion or flat"),
    ("bad-hero-title-size", "sections:\n  - type: hero\n    data:\n      title: Bad\n      title_size: calc(100vw)\n", "hero.title_size must be a CSS length in rem, em, or px"),
    ("bad-marquee", "sections:\n  - type: logo-wall\n    data:\n      layout: carousel\n      items: [{title: Logo}]\n", "layout must be grid or marquee"),
    ("bad-compare", "sections:\n  - type: pricing-compare\n    data:\n      tiers: [Free, Pro]\n      groups:\n        - name: Group\n          rows: [{name: Row, cells: [Y]}]\n", "has 1 cells for 2 tiers"),
    ("bad-bar", "sections:\n  - type: bar-chart\n    data:\n      items: [{label: Bad, value: nope}]\n", "value must be numeric"),
)


def check_invalid(hugo: str) -> list[str]:
    errors: list[str] = []
    for name, data, expected in INVALID_CASES:
        with tempfile.TemporaryDirectory(prefix=f"td-landing-components-landing-{name}-") as temp:
            site = Path(temp)
            create_site(site, data)
            result = run(hugo, site)
            output = result.stdout + result.stderr
            require(result.returncode != 0, f"invalid landing case {name} unexpectedly built", errors)
            require(expected in output, f"invalid landing case {name} did not report {expected!r}", errors)
    return errors


def check_localized_fields(hugo: str) -> list[str]:
    errors: list[str] = []
    data = """sections:
  - type: pricing
    data:
      tiers:
        - name: Base name
          name_zh: Primary name
          name_zh_cn: Full name
          price: Free
        - name: Base fallback
          price: Free
"""
    with tempfile.TemporaryDirectory(prefix="td-landing-components-landing-fields-") as temp:
        site = Path(temp)
        create_site(site, data, language="zh-cn")
        result = run(hugo, site)
        if result.returncode != 0:
            errors.append(f"localized field fixture failed: {result.stdout}{result.stderr}")
        else:
            source = (site / "public/test/index.html").read_text(encoding="utf-8")
            require("Full name" in source, "full language field did not win", errors)
            require("Base fallback" in source, "unsuffixed field fallback failed", errors)
            require("Primary name" not in source, "primary field overrode a full-language field", errors)
            for marker in ('id="td-section-nav"', 'class="td-shell-sidebar', 'class="td-toc'):
                require(marker not in source, f"typed landing fixture inherited article chrome: {marker}", errors)
    return errors


def check_rss(hugo: str) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="td-landing-components-landing-rss-") as temp:
        site = Path(temp)
        create_site(site, "sections:\n  - type: command-box\n    data: {title: Install, code: echo secret}\n")
        config = (site / "hugo.yaml").read_text(encoding="utf-8")
        write(
            site / "hugo.yaml",
            config.replace("disableKinds: [home, RSS,", "disableKinds: [home,").replace("page: [HTML]", "page: [HTML, RSS]"),
        )
        page = (site / "content/test.md").read_text(encoding="utf-8")
        write(site / "content/test.md", page.replace("---\n", "outputs: [HTML, RSS]\n---\n", 1))
        result = run(hugo, site)
        if result.returncode != 0:
            errors.append(f"landing RSS fixture failed: {result.stdout}{result.stderr}")
        else:
            outputs = list((site / "public/test").glob("*.xml"))
            require(len(outputs) == 1, "landing RSS fixture did not emit exactly one feed output", errors)
            if outputs:
                source = outputs[0].read_text(encoding="utf-8")
                for marker in ("echo secret", "td-landing-", "data-td-landing"):
                    require(marker not in source, f"landing RSS leaked {marker}", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hugo", default="hugo")
    parser.add_argument("--public", type=Path)
    args = parser.parse_args()

    if args.public is None:
        with tempfile.TemporaryDirectory(prefix="td-landing-components-landing-example-") as temp:
            public = Path(temp) / "public"
            result = run(args.hugo, EXAMPLE, public)
            if result.returncode != 0:
                print("landing fixture failed to build:")
                print(result.stdout + result.stderr)
                return 1
            errors = check_example(public)
    else:
        errors = check_example(args.public)
    errors += check_sources() + check_invalid(args.hugo) + check_localized_fields(args.hugo) + check_rss(args.hugo)
    if errors:
        print("landing checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("landing checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
