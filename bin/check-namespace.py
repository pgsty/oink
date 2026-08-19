#!/usr/bin/env python3
"""Freeze the theme's public naming surface.

Over the built exampleSite (--public, default exampleSite/public):

  1. every class the theme generates starts with `td-`;
  2. every data attribute the theme generates starts with `data-td-`;
  3. every CSS custom property the theme defines starts with `--td-`.

Third-party markup (Bootstrap, Font Awesome, KaTeX, Chroma, Giscus, Swagger
UI, ReDoc, Mermaid, asciinema) and the documented unprefixed *author* markers
keep their own names; both are allowlisted below and nothing else is.

The point is not tidiness. `.leaf`, `.is-open`, `data-url`, and `--oink-ink`
in a theme's global stylesheet collide with whatever the consuming site and
its authors already use, and a theme cannot take a name back after 1.0.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Author-facing markers: an author types these, so they stay unprefixed.
# docs/components.md owns the public marker namespace.
AUTHOR_MARKERS = {
    "steps", "cards", "fields", "matrix", "full-width", "no-step-marker",
}

# Classes emitted by third-party runtimes or by Hugo/Goldmark itself.
THIRD_PARTY_CLASS = re.compile(
    r"^("
    # Bootstrap layout, components and utilities
    r"d-|col($|-)|row$|container($|-)|btn($|-)|nav-(link|item|tabs)$|navbar($|-)|form-|input-"
    r"|text-|bg-|border($|-)|[mp][sebtxy]?-(auto|\d|sm|md|lg|xl|xxl)|g-\d|gap-|align-|justify-|flex-|order-"
    r"|w-|h-|position-|top-|start-|end-|bottom-|visually-|fs-\d|fw-|lh-|rounded|shadow($|-)"
    r"|dropdown($|-)|collapse($|-)|collapsing$|show$|active$|disabled$|fade$|offcanvas($|-)"
    r"|badge$|list-|table($|-)|card($|-)|accordion($|-)|modal($|-)|small$|lead$|float-"
    r"|overflow-|user-select-|z-\d|opacity-|ratio($|-)|img-|figure($|-)|blockquote($|-)"
    r"|mark$|sr-only|clearfix$|stretched-link$|vstack$|hstack$|h[1-6]$|display-\d"
    r"|tab-(pane|content)$|pagination$|page-(item|link)$|offset-|invisible$|visible$"
    r"|breadcrumb($|-)|alert($|-)|close$|spinner-|progress($|-)|placeholder($|-)"
    # Swagger UI renders its own .info .title inside .swagger-ui
    r"|info$|title$|content$|scheme|opblock|model|response|parameter"
    # Font Awesome
    r"|fa[brsl]?$|fa-"
    # KaTeX
    r"|katex|mord|mtight|mathnormal|pstrut|mspace|vlist|size\d|sizing$|reset-size\d|base$"
    r"|strut$|m(bin|rel|op|open|close|inner|frac|punct)$|msupsub$|nulldelimiter$|delim"
    r"|frac-line$|op-|large-op$|sqrt$|svg-align$|hide-tail$|accent|overline$|underline$"
    r"|mtable$|col-align|arraycolsep$|rlap$|llap$|inner$|fix$|vbox$|thinbox$|eqn-num$|tag$"
    r"|newline$|boxpad$|angl|cd-|fbox$|fcolorbox$|not$|textbf$|textit$|mspace$|mathdefault$"
    r"|math(rm|bf|it|bb|cal|frak|scr|sf|tt)$|text(rm|sf|tt|bb)?$|boldsymbol$|amsrm$|mainrm$"
    r"|stretchy$|x-arrow|halfarrow-|brace-|mult$|delim-size\d$|mtr-glue$|vertical-separator$"
    # KaTeX again: \vdots rules, small \sum, and the CJK fallback \text{} takes
    r"|rule$|small-op$|cjk_fallback$"
    # Chroma / Hugo highlighting
    r"|chroma$|highlight$|line$|lnt?$|lntable$|lntd$|lnlinks$|hl$|cl$|language-|[a-z]{1,3}\d?$"
    # Hugo / Goldmark
    r"|footnotes$|footnote-|task-list-item$"
    # Giscus, Swagger UI, ReDoc, Mermaid, asciinema, external SVG loader
    r"|giscus|swagger|redoc|mermaid|ap-|markmap|drawio|DocSearch|gsc?-|gsc"
    r")"
)

# Data attributes required by a third-party runtime's own API.
THIRD_PARTY_DATA = {
    # Giscus embed contract
    "data-repo", "data-repo-id", "data-category", "data-category-id", "data-mapping",
    "data-strict", "data-reactions-enabled", "data-emit-metadata", "data-input-position",
    "data-theme", "data-lang", "data-loading",
    # Bootstrap
    "data-bs-theme", "data-bs-toggle", "data-bs-target", "data-bs-placement",
    "data-bs-container", "data-bs-original-title", "data-bs-theme-value", "data-bs-dismiss",
    "data-bs-parent", "data-bs-slide", "data-bs-slide-to", "data-bs-ride", "data-bs-backdrop",
    # html-proofer opt-out honoured by consuming sites' CI
    "data-proofer-ignore",
    # documented author opt-out, in the same family as the {.cards} markers
    "data-no-zoom",
    # Authored data-* attributes pass through by contract
    # The shared attribute policy permits site-owned classes.
    "data-note",
}

# Custom properties a third-party runtime reads from its own stylesheet: the
# theme sets them to theme its player, so they cannot carry a --td- prefix.
# asciinema-player.css reads --term-* (palette, font, metrics); renaming them
# leaves the player on its built-in black-on-white defaults inside an OINK
# terminal surface, which is how the 0.5 sweep broke it.
THIRD_PARTY_PROPERTY = re.compile(
    r"^--term-(color-(foreground|background|\d+)|font-family|line-height|cols|rows)$"
)
PLAYER_THEME_RE = re.compile(
    r"asciinema-player-theme-(td-light|td-dark)\s*\{[^}]*--term-color-background\s*:"
)

CLASS_RE = re.compile(r'class="([^"]*)"')
# Only a real attribute assignment counts; prose such as "data-driven
# sections" in page copy is not markup.
DATA_RE = re.compile(r"[\s<](data-[a-z0-9-]+)=")
CUSTOM_PROPERTY_RE = re.compile(r"(?:^|[;{\s])(--[a-z][a-z0-9-]*)\s*:")
# Font Awesome sets a bare `--fa` plus its `--fa-*` family.
ALLOWED_PROPERTY_PREFIX = ("--td-", "--bs-", "--fa")


def scan_html(public: Path) -> tuple[Counter[str], Counter[str], int]:
    classes: Counter[str] = Counter()
    attributes: Counter[str] = Counter()
    pages = 0
    for path in sorted(public.rglob("*.html")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        pages += 1
        for match in CLASS_RE.finditer(text):
            for token in match.group(1).split():
                classes[token] += 1
        for match in DATA_RE.finditer(text):
            attributes[match.group(1)] += 1
    return classes, attributes, pages


def check_html(public: Path) -> list[str]:
    errors: list[str] = []
    classes, attributes, pages = scan_html(public)
    if pages == 0:
        return ["no HTML pages found — build exampleSite first"]

    stray_classes = sorted(
        name
        for name in classes
        if not name.startswith("td-")
        and name not in AUTHOR_MARKERS
        and not THIRD_PARTY_CLASS.match(name)
        # exampleSite fixtures use their own site-local classes on purpose
        and "fixture" not in name
    )
    for name in stray_classes:
        errors.append(f"class {name!r} is theme-generated but not td- prefixed ({classes[name]}×)")

    stray_attributes = sorted(
        name
        for name in attributes
        if not name.startswith(("data-td-", "data-bs-")) and name not in THIRD_PARTY_DATA
    )
    for name in stray_attributes:
        errors.append(f"attribute {name!r} is theme-generated but not data-td- prefixed ({attributes[name]}×)")
    return errors


def check_css(public: Path) -> list[str]:
    errors: list[str] = []
    seen = 0
    for path in sorted(public.rglob("*.css")):
        # Vendored stylesheets keep their own custom properties.
        if "third_party" in path.as_posix() or path.name.startswith(("katex", "swagger", "giscus")):
            continue
        seen += 1
        for name in set(CUSTOM_PROPERTY_RE.findall(path.read_text(encoding="utf-8", errors="ignore"))):
            if not name.startswith(ALLOWED_PROPERTY_PREFIX) and not THIRD_PARTY_PROPERTY.match(name):
                errors.append(f"{path.name}: custom property {name} is outside the --td- namespace")
    if seen == 0:
        errors.append("no theme stylesheet found in the build")
    return errors


def check_sources() -> list[str]:
    """Guard source-level namespaces and the rendered DOM/JS dataset contract."""
    errors: list[str] = []
    js = list((ROOT / "assets/js").glob("*.js"))
    globals_set = set()
    for path in js:
        text = path.read_text(encoding="utf-8")
        globals_set |= set(re.findall(r"window\.([A-Z][A-Za-z0-9_]*)\s*=", text))
        globals_set |= set(re.findall(r"window\.(td[A-Za-z0-9_]*)", text))
    for name in sorted(globals_set):
        if not name.startswith("Oink") and name not in {"HTMLDialogElement"}:
            errors.append(f"window.{name} is outside the Oink* global namespace")

    # `data-td-copy-mode` is exposed as `dataset.tdCopyMode`, not
    # `dataset.copyMode`. The 0.5 namespace migration updated selectors but a
    # camelCase dataset accessor contains no `data-` token for grep to find, so
    # stale readers can otherwise pass every output check while returning
    # undefined in the browser. Verify every direct accessor against the source
    # attribute vocabulary and allow only third-party or private bookkeeping
    # keys that deliberately stay unprefixed.
    source_files = (
        list((ROOT / "layouts").rglob("*.html"))
        + list((ROOT / "layouts").rglob("*.xml"))
        + list((ROOT / "assets").rglob("*.js"))
        + list((ROOT / "assets").rglob("*.scss"))
    )
    vocabulary = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in source_files)
    allowed_unprefixed = {
        "command-palette.js": {"paletteRow"},
        "page-actions.js": {"original"},
        # These are Giscus' own embed API plus one private idempotency marker.
        "giscus.js": {
            "theme", "loaded", "repo", "repoId", "category", "categoryId",
            "mapping", "strict", "reactionsEnabled", "emitMetadata",
            "inputPosition", "lang", "loading", "term",
        },
    }

    def kebab(value: str) -> str:
        return re.sub(r"(?<!^)([A-Z])", r"-\1", value).lower()

    for path in js:
        text = path.read_text(encoding="utf-8")
        for prop in sorted(set(re.findall(r"\.dataset\.([A-Za-z][A-Za-z0-9_]*)", text))):
            if prop.startswith("td") and len(prop) > 2 and prop[2].isupper():
                attribute = "data-td-" + kebab(prop[2:])
            else:
                attribute = "data-" + kebab(prop)
                if prop in allowed_unprefixed.get(path.name, set()):
                    continue
                else:
                    errors.append(
                        f"{path.name}: dataset.{prop} is outside the td* dataset namespace"
                    )
                    continue
            if attribute not in vocabulary:
                errors.append(
                    f"{path.name}: dataset.{prop} has no matching {attribute} source attribute"
                )

    feedback = (ROOT / "assets/js/feedback.js").read_text(encoding="utf-8")
    for marker in ("data(root, 'tdPagePath')", "data(root, 'tdLanguage')"):
        if marker not in feedback:
            errors.append(f"feedback.js does not read the namespaced identity through {marker}")

    # The other half of the THIRD_PARTY_PROPERTY exception: asciinema's palette
    # reaches the player only under the player's own names. A --td-term-*
    # variant compiles, passes every other check, and leaves the terminal on
    # asciinema's built-in black inside a light OINK window — the 0.5 break.
    scss = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "assets/scss").rglob("*.scss"))
    )
    themed = set(PLAYER_THEME_RE.findall(scss))
    for variant in ("td-light", "td-dark"):
        if variant not in themed:
            errors.append(
                f"asciinema-player-theme-{variant} does not set --term-color-background "
                "(the player reads --term-*, never --td-term-*)"
            )

    # Same family as the asciinema exception, one level up: two vendored
    # runtimes carry a complete dark palette of their own but key it on their
    # own switch, not on `data-bs-theme`. The theme reaches those palettes only
    # by mirroring its resolved mode onto both names, at first paint and on
    # every later toggle. Drop either and the runtime silently stays light --
    # Swagger UI's body text falls to 1.86:1 on the dark page.
    theme_runtime = (ROOT / "assets/js/dark-mode.js").read_text(encoding="utf-8")
    head = (ROOT / "layouts/_partials/head.html").read_text(encoding="utf-8")
    for label, source in (("dark-mode.js", theme_runtime), ("head.html", head)):
        for marker, vendor in (
            ("classList.toggle('dark-mode'", "Swagger UI"),
            ("setAttribute('data-theme'", "Algolia DocSearch"),
        ):
            if marker not in source:
                errors.append(
                    f"{label} does not mirror the colour mode onto {vendor}'s own switch "
                    f"({marker}...)"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", type=Path, default=ROOT / "exampleSite/public")
    args = parser.parse_args()

    errors = check_html(args.public) + check_css(args.public) + check_sources()
    if errors:
        print("Namespace checks failed:")
        for error in errors:
            print(f"  {error}")
        return 1
    print("Namespace checks passed (td- classes, data-td- attributes, --td- properties, Oink* globals)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
