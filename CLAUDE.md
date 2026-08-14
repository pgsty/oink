# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

`github.com/pgsty/oink` is a Hugo theme published as a **Hugo Module** — the
repository root *is* the module. It is a hard fork of [Docsy](https://github.com/google/docsy)
that absorbs ideas from FumaDocs, Hextra, and Nextra: Docsy's content model and
`td-` naming survive underneath, but the shell, navigation, search, content
primitives, and typography system are OINK's own.

There is **no site, no npm workspace, and no build step** here. Hugo Extended is
the only build tool. `exampleSite/` is a deliberately minimal fixture site used
by the check scripts and CI — not a showcase.

### Two-repo model

| Repo | Contains |
| --- | --- |
| `pgsty/oink` (this one) | layouts, partials, shortcodes, SCSS, JS, i18n, vendored assets, `hugo.yaml`, `VENDOR.json` |
| `pgsty/oink.pgsty.com` | bilingual docs site, regression fixtures, Playwright/Node test suite, deployment |

The sites are developed as siblings under `~/pgsty/`. The site repo pins a
released theme tag in its `go.mod`; local cross-repo work goes through an
ignored `go.work` (`HUGO_MODULE_WORKSPACE=go.work`) that replaces the module
with `../oink`. Never commit a filesystem `replace` into either module.

Theme branches: `main` = next release, `release` = current stable, `vX.Y.Z` tags
are immutable. Site repo has only `main`.

## Commands

### Theme repo (this one)

Everything CI runs, in order — see `.github/workflows/ci.yml`:

```sh
# Source-level contract checks (no build needed)
python3 scripts/check-i18n.py                        # translation key parity across 32 locales
python3 scripts/check-i18n.py --sync                 # append missing keys as English fallbacks
python3 scripts/check-font-tokens.py                 # no raw font families outside the token layer
python3 scripts/check-content-primitives-contract.py # docs/content-primitives.md still has required sections
python3 scripts/check-prd4-contract.py               # navigation/palette/action contracts
python3 scripts/check-prd4-runtime.py                # runtime isolation and capability predicates
python3 scripts/check-sidebar-icons.py               # sidebar icon density policy
python3 scripts/check-prd4-search.py                 # search metadata and ranking
python3 scripts/check-prd4-actions.py                # action registry and command manifest
python3 scripts/check-prd4-palette.py                # Command Palette modes and behavior
python3 scripts/check-prd4-docs.py                   # bilingual migration and starter guidance
python3 scripts/check-prd5-contract.py               # PRD 5 human/machine contract alignment
python3 scripts/check-prd5-docs.py                   # PRD 5 bilingual migration + root/subpath starter
python3 scripts/check-prd5-reading.py                # math passthrough + tree-order pager
python3 scripts/check-release-assets.py              # release facts/cards/checksum output matrix
python3 scripts/check-download.py                    # download schema and publication states
python3 scripts/check-landing.py                     # landing registry/runtime/output matrix
python3 scripts/check-book.py                        # numbered targets/xrefs/Book assembly
python3 scripts/check-prd5-migrations.py              # dry-run/idempotency Book migration profiles
python3 scripts/check-prd5-misc.py                    # shared scenario fixes and compatibility

cd exampleSite && hugo --printPathWarnings --panicOnWarning   # must build warning-free

# Output checks (each builds exampleSite into a temp dir itself)
python3 scripts/check-code-blocks.py        # enhanced fences / code groups
python3 scripts/check-content-primitives.py # badge, kbd, fields, filetree
python3 scripts/check-media-primitives.py   # image resolver + imgproc compatibility
python3 scripts/check-image-zoom.py         # zoom gating and output isolation
python3 scripts/check-gallery.py            # gallery + zoom runtime reuse

# Browser runtimes (plain assets, no install step)
node --test 'tests/js/**/*.test.js'
```

The output-checking scripts accept `--hugo /path/to/hugo` (to test the 0.160.1
floor) and `--public DIR` (to reuse an existing build). Run a single one
directly; there is no aggregate target.

`tests/js/` unit-tests the browser runtimes (`action-registry`,
`command-palette`, `palette-model`, `search-engine`, `surfaces`, `page-actions`,
`dark-mode`) headlessly — each runtime exports itself on `window` and under
`module.exports` for exactly this. Add coverage there when changing
`assets/js/`; it is the only automated check on that code in this repository.

Interactive preview of the fixture site:

```sh
cd exampleSite && hugo server
```

CI additionally verifies the `system` typography preset
(`HUGO_PARAMS_UI_TYPOGRAPHY_PRESET=system` must emit
`data-td-typography="system"`), that legacy Sass font overrides in a consumer's
`_variables_project.scss` still win, and that an invalid preset **fails the
build** with `invalid params.ui.typography.preset`.

CI matrix: Hugo Extended `0.160.1` (the floor, declared in `hugo.yaml` and
`theme.toml`) and `0.164.0`. Anything requiring a newer Hugo feature is out of
bounds.

### Site repo (`../oink.pgsty.com`) — where behavioral changes get verified

Make targets wire up `go.work` automatically:

```sh
make d   # dev server against the sibling theme checkout (make dev PORT=1314)
make b   # build
make c   # full suite (npm test)
```

Narrowest useful npm scripts:

```sh
npm run test:hugo-build   # node --test: blog metadata, RSS, primitives, deprecation-free build
npm run test:md-output    # golden Markdown/llms.txt output  (update: npm run update:md-goldens)
npm run test:alt-site     # alternate-config builds from tests/fixtures/*.yml
npm run test:favicons     # golden head output (update: npm run update:favicon-goldens)
npm run test:browser      # all Playwright suites
npx playwright test tests/browser/code-blocks.spec.mjs   # one browser spec
npm run check:format      # prettier; fix with npm run fix:format
node scripts/check-doc-translations.mjs --public public  # rendered heading-ID parity
```

Playwright starts its own Hugo server on `127.0.0.1:4173` unless
`PLAYWRIGHT_BASE_URL` is set. Node ≥24 / npm ≥11.16 required there.

## Architecture

### Build model

Hugo resolves content + config + theme templates + committed assets and emits
`public/`. SCSS goes through Hugo Extended's embedded Sass transpiler
(`resources.ToCSS` in `_partials/head-css.html`); `postCSS` is never invoked.
Production runs `minify | fingerprint` and emits SRI attributes. Bootstrap's RTL
stylesheet is shipped as a prebuilt artifact rather than running `rtlcss`.

### Page shell

`layouts/baseof.html` and the type-specific `layouts/{docs,blog,swagger}/baseof.html`
assemble the shell from small partials in `layouts/_partials/shell/`
(`sidebar-tree`, `toc-aside`, `subnav`, `search-dialog`, `root-menu`,
`taxonomy-filter`, …). Shell activation is **type-based, not path-based**:
`params.ui.shell_types` (default `docs, blog, swagger`) decides, so a site can
place docs anywhere and assign `type: docs` via a front-matter cascade.
`params.ui.docs_section` / `blog_section` only name the roots for navigation.
`_partials/shell/config.html` is the single `return`-style resolver for
brand/logo/section config — read it before adding a new shell parameter.

When extending, override the narrowest partial. Do not copy `baseof.html`.

### Conditional runtime loading (the central mechanism)

Shortcodes and render hooks set flags on the Hugo **Page Store**
(`hasEcharts`, `hasAsciinema`, `hasmermaid`, `hasCodeRuntime`, `hasTabpane`,
`hasImageZoom`, `hasGiscus`, `hasFeedback`, …). `_partials/scripts.html` reads
those flags afterwards and concatenates exactly the runtimes the page used —
once per page, regardless of instance count — into a bundle whose name is an
md5 of the flag combination. A page that uses nothing gets Bootstrap + base +
sidebar-nav + a11y only.

Consequences that constrain every new feature:

- Content must render **before** `scripts.html` runs. `_partials/content/render.html`
  is the single wrapper that renders `.Content` and registers derived flags
  (currently the Image Zoom candidate scan); page layouts call it instead of
  `.Content` directly.
- Flags are set by shortcodes/partials, read by asset assembly. Shortcodes must
  never read a flag another shortcode might set later.
- A new flag must be added to the `$bundleKey` list or two pages with different
  feature sets will collide on one bundle filename.

### Output-format matrix

`Page.Store` key `tdOutputFormat` (`html` | `print` | `markdown` | `rss`) is set
at the top of every `baseof*` template and in the RSS/print renderers, then read
by every component that must degrade. The theme declares custom output formats
`LLMS` (`llms.txt`) and `print`; consuming sites opt into `markdown`, `LLMS`,
and `print` in their own `outputs:` config — the theme never forces them.

Every content primitive must produce sensible output in all four: interactive
HTML, static print HTML (zoom/copy affordances stripped, disclosures expanded),
plain Markdown (`layouts/all.md`, byte-compared against goldens in the site
repo), and RSS. `_partials/content/static-image-output.html` strips interactive
attributes for non-HTML outputs; its regexes are attribute-precise, so change
them carefully.

### Typography tokens

Fonts live behind `--td-*-font-family` custom properties
(`ui`, `body`, `heading`, `code`, `display`, `metadata`, `print`) defined in
`assets/scss/td/_tokens-typography.scss`. `params.ui.typography.preset` selects
`technical` (default, OINK brand faces) or `system` (platform stack, no brand
font requests); both compile into the same stylesheet, no JS. Existing Docsy /
Bootstrap Sass font variables seed the roles, so legacy consumer overrides keep
working — `check-font-tokens.py` enforces that raw family names appear only in
the allowlisted files (`_brand.scss`, `_tokens-typography.scss`,
`_variables_forward.scss`, `_variables.scss`). See `docs/typography-tokens.md`.

### Local-first constraints (non-negotiable)

A theme-owned feature must not depend on a CDN, a build-time download, or an
unconfigured public service. Vendored runtimes live under
`assets/third_party/` (Lunr is the exception: its code sits in
`assets/js/third_party/` with its license under `assets/third_party/lunr/`) —
that path (not `vendor/`) because Go excludes `vendor`
from published modules. `VENDOR.json` records version, source, license files,
artifact paths, and SHA-256 for each; updating a runtime means refreshing
artifact + license + checksum together.

The theme deliberately **errors the build** rather than silently reaching out:
PlantUML without `params.plantuml.svg_image_url`, Diagrams.net without
`params.drawio.drawio_server`, and Algolia without explicit
`appId`/`apiKey`/`indexName` all `errorf`. Preserve that pattern for anything
new that could imply a network call.

### Internationalization

32 locale files in `i18n/` share one key schema; `check-i18n.py` enforces exact
key parity and ordering. English, `zh-cn`, `zh`, and `zh-tw` are reviewed; other
locales carry inherited Docsy translations plus explicit English fallbacks for
OINK-only keys. Adding a user-visible string means adding the key to **all 32**
files (`--sync` does the mechanical part).

## Frozen contracts

`docs/content-primitives.md`, `docs/enhanced-code-blocks.md`,
`docs/typography-tokens.md`, and the three `docs/prd5-*-contract.md` files are
implementation contracts, not tutorials. The
first is machine-checked for structure by `check-content-primitives-contract.py`.
They define the public shortcode APIs (Badge, Kbd, Fields/Field, FileTree,
imgproc, Image Zoom, Gallery/Gallery Image, Release Assets, numbered Book
components, and xref; enhanced fences and code groups), parameter validation,
escaping and URL policy, ID generation, and the output matrix. **Read the
relevant contract before changing a primitive**, and change the contract in the
same commit as the behavior.

Recurring rules from those contracts:

- Standard shortcode notation `{{< … >}}`; nested names (`filetree/folder`,
  `gallery/image`, `field`) are part of the public API and are valid only inside
  their parent.
- Collector shortcodes evaluate `.Inner` so children register ordered data; the
  parent owns all rendering. Shortcodes do not write Page Store flags that other
  shortcodes read.
- Invalid parameters `errorf` — strict failure over silent degradation.
- Only Fields descriptions accept Markdown (via `.Page.RenderString`); every
  other public string parameter is plain text.
- CSS must handle `forced-colors`, reduced motion, print, and RTL (use logical
  properties).

## Conventions

- **No `oink.*` config tree, no `oink.enabled` switch, no parallel visual
  shell.** The standard layouts are the product; upstream Docsy changes are
  ported into the single canonical implementation rather than gated behind a
  brand switch.
- Theme parameters live under `params.ui.*` in `hugo.yaml`; theme defaults there
  are intentionally conservative — interactive features (`offlineSearch`,
  `ui.image_zoom.enable`, `comments.enable`, `ui.feedback.enable`) are opt-in so
  the theme never sets site policy.
- Code highlighting goes through `layouts/_markup/render-codeblock.html`, not
  `markup:` config (Hugo ignores `markup` set by a theme).
- Docsy heritage: keep `td-` prefixes, existing Sass variables, documented
  compatibility aliases, upstream copyright headers, and `NOTICE`.
- `public/` and `resources/` are gitignored in both repos despite appearing in a
  working tree; never commit generated output.
- Site docs are bilingual: any page added under the site's `content/docs/` or
  `content/blog/` needs a `.zh.md` peer with explicit heading IDs copied from
  the rendered English HTML (`TRANSLATION.md` in the site repo).

## Release states

Distinct and not interchangeable — report the actual one:
source complete → validated (theme checks + site suite) → published (immutable
signed `vX.Y.Z` root tag resolving through the Go proxy) → documented (site pins
the tag) → deployed. A green local build is none of these. Tags are never moved;
a mistake gets a new patch version.
