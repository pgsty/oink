# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

`github.com/pgsty/oink` is a Hugo theme published as a **Hugo Module** — the
repository root *is* the module. It is a hard fork of [Docsy](https://github.com/google/docsy)
that absorbs ideas from FumaDocs, Hextra, and Nextra: Docsy's content model and
`td-` naming survive underneath, but the shell, navigation, search, content
primitives, and typography system are OINK's own.

There is **no site, no npm workspace, and no build step** here. Hugo Extended is
the only build tool. `exampleSite/` is the bilingual (`en` + `zh`) public
component reference: Docs, Blog, and Book stay small enough to read as examples.
Narrow behaviour pins live under `tests/site/`; check scripts merge
`tests/site/hugo.yaml` with the example config, so regression-only pages and
media never ship in the public example build.

### Two-repo model

| Repo | Contains |
| --- | --- |
| `pgsty/oink` (this one) | layouts, partials, shortcodes, SCSS, JS, i18n, vendored assets, `hugo.yaml`, `VENDOR.json` |
| `pgsty/oink.pgsty.com` | bilingual docs site, regression fixtures, Playwright/Node test suite, deployment |

The sites are developed as siblings under `~/pgsty/`. The site repo pins a
released theme tag in its `go.mod`; local cross-repo work goes through an
ignored `go.work` (`HUGO_MODULE_WORKSPACE=go.work`) that replaces the module
with `../oink`. Never commit a filesystem `replace` into either module.

Theme branches: `main` = next release; `release` = current stable, created at
the 0.5.0 tag (there is none before it); `vX.Y.Z` tags are immutable and
only count as published once pushed (0.4.2 was tagged locally but never
pushed). Site repo has only `main`.

## Commands

### Theme repo (this one)

Everything CI runs, in order — see `.github/workflows/ci.yml`:

```sh
# Source-level contract checks (no build needed)
python3 bin/check-i18n.py                        # translation key parity across 32 locales
python3 bin/check-i18n.py --sync                 # append missing keys as English fallbacks
python3 bin/check-taxonomy.py                    # opt-in taxonomy labels and bilingual output
python3 bin/check-font-tokens.py                 # no raw font families outside the token layer
python3 bin/check-navigation-contract.py         # navigation/palette/action contracts
python3 bin/check-runtime-isolation.py           # runtime isolation and capability predicates
python3 bin/check-sidebar-icons.py               # sidebar icon density policy
python3 bin/check-search.py                      # search metadata and ranking
python3 bin/check-actions.py                     # action registry and command manifest
python3 bin/check-palette.py                     # Command Palette modes and behavior
python3 bin/check-starter.py                      # root/subpath starter and component wiring
python3 bin/check-reading.py                     # math passthrough + tree-order pager
python3 bin/check-release-assets.py              # release facts/cards/checksum output matrix
python3 bin/check-download.py                    # download schema and publication states
python3 bin/check-landing.py                     # landing registry/runtime/output matrix
python3 bin/check-book.py                        # numbered targets/xrefs/Book assembly
python3 bin/check-book-migrations.py             # dry-run/idempotency Book migration profiles
python3 bin/check-shared-scenarios.py            # shared scenario fixes and compatibility
python3 bin/check-keyboard.py                    # keyboard navigation contract
python3 bin/check-shell.py                       # navigation and page-end composition
python3 bin/check-annotation.py                  # page annotation: upstream attribution, licence table, translation notice
python3 bin/check-namespace.py                   # td- class / data-td- attribute / --td- property namespaces
python3 bin/check-params.py                      # parameter shapes (bare booleans, no single-key maps, FM = site key minus ui.) + legacy-key build matrix
python3 bin/check-site-markup.py --site exampleSite # consuming-site Goldmark prerequisites
python3 bin/check-output.py                      # HTML structure, duplicate IDs, bundle graph, output security (+ negative fixture)
python3 bin/check-goldens.py                     # four-state goldens (html / print / markdown / rss / llms) of exampleSite

cd exampleSite && hugo --printPathWarnings --panicOnWarning   # must build warning-free

# Output checks (each builds exampleSite into a temp dir itself)
python3 bin/check-code-blocks.py                 # enhanced fences / adjacent-fence tabs / tabs shortcode
python3 bin/check-content-primitives.py # badge, kbd, fields (table + shortcode), filetree/steps/cards lists, table family
python3 bin/check-media-primitives.py            # image render hook and shared resolver
python3 bin/check-image-zoom.py                  # zoom gating and output isolation
python3 bin/check-gallery.py                     # native gallery list + zoom runtime reuse
python3 bin/check-components.py                  # callouts, tabs, data fences, removed shortcodes, hook attribute policy

# Content migration toolkit for the 0.4 -> v5 syntax (dry-run by default; tests in tests/migrations/)
python3 bin/migrations/oink06.py report --sites <dir>... # read-only inventory
python3 bin/migrations/oink06.py migrate --site <dir> [--write]
python3 bin/migrations/oink06.py check --site <dir> # residual legacy syntax
python3 -m unittest discover -s tests/migrations -t .

# Browser runtimes (plain assets, no install step)
node --test 'tests/js/**/*.test.js'
```

`check-output.py` and `check-goldens.py` also read `exampleSite/public` (or `--public`); `check-goldens.py --update` rewrites `tests/goldens/` — do it in the same commit as the behaviour change and say why. `bin/check-output-security.py --public DIR --base-url URL [--third-party]` is the product-level trust check any site can run; `bin/sites/build-all.py` builds the eleven sites strictly in isolation (`--ref <branch>`, `--keep`, `--baseline` for surface diffs).

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

CI additionally builds one small consumer site in Hugo Module mode
(`HUGO_MODULE_REPLACEMENTS` pointing at the checkout) so module-only path
resolution is exercised, verifies the `system` typography preset
(`HUGO_PARAMS_UI_TYPOGRAPHY=system` must emit
`data-td-typography="system"`), that legacy Sass font overrides in a consumer's
`_variables_project.scss` still win, and that an invalid preset **fails the
build** with `invalid params.ui.typography`.

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
`params.ui.shell_types` (default `docs, book, blog, swagger`) decides, so a site can
place docs anywhere and assign `type: docs` via a front-matter cascade.
`params.ui.docs_section` / `blog_section` only name the roots for navigation.
`_partials/shell/config.html` is the single `return`-style resolver for
brand/logo/section config — read it before adding a new shell parameter.

When extending, override the narrowest partial. Do not copy `baseof.html`.

### Conditional runtime loading (the central mechanism)

Shortcodes and render hooks set flags on the Hugo **Page Store**
(`hasEcharts`, `hasAsciinema`, `hasmermaid`, `hasCodeRuntime`, `hasTabs`,
`hasImageZoom`, `hasGiscus`, `hasFeedback`, …). `_partials/scripts.html` reads
those flags afterwards and concatenates exactly the runtimes the page used —
once per page, regardless of instance count — into a bundle whose name is an
md5 of the member list. A page that uses nothing gets Bootstrap, base,
navbar-menu, and sidebar-nav only.

Consequences that constrain every new feature:

- Content must render **before** `scripts.html` runs. `_partials/content/render.html`
  is the single wrapper that renders `.Content` and registers derived flags
  (currently Image Zoom and authored-content accessibility); page layouts call it instead of
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
`assets/scss/td/_tokens-typography.scss`. `params.ui.typography` selects
`technical` (default, OINK brand faces) or `system` (platform stack, no brand
font requests); both compile into the same stylesheet, no JS. Existing Docsy /
Bootstrap Sass font variables seed the roles, so legacy consumer overrides keep
working — `check-font-tokens.py` enforces that raw family names appear only in
the allowlisted files (`_brand.scss`, `_tokens-typography.scss`,
`_variables_forward.scss`, `_variables.scss`). See `docs/architecture.md`.

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

## Implementation contracts

`docs/README.md` indexes the current maintainer notes. `architecture.md`,
`components.md`, `shell.md`, `landing-contract.md`, and `migration.md` describe
the active 0.5 behavior; history belongs in Git and `CHANGELOG.md`. Behavioral
checks and rendered goldens are executable authority, so do not add tests that
only pin prose. Read and update the relevant note when changing a public
contract.

The component surface has native forms (`> [!TYPE]` callouts; `{.steps}` and
`{.cards}` lists; table/image attributes; adjacent-fence tabs; data fences such
as `filetree` and `gallery`) and 29 shortcodes (core 14, Book 10, Release 3,
OpenAPI 2). The complete inventory and output matrix are in
`docs/components.md`.

Recurring rules from those contracts:

- `{{% steps %}}` is the only `{{% %}}` shortcode (its body is top-level page
  Markdown); every other shortcode uses `{{< … >}}` and renders Markdown bodies
  through `content/render-block.html` (`RenderString` in a scoped context).
  Nested names (`tab`, `card`, `field`) are valid only inside their parent.
- Collector shortcodes evaluate `.Inner` so children register ordered data; the
  parent owns all rendering. Shortcodes do not write Page Store flags that other
  shortcodes read.
- **The theme never calls `errorf`. Ever.** Invalid input `warnf`s and falls
  back to the documented default, and the build keeps going. Use
  `partial "validate.html"` (enum/bool/length shapes) rather than hand-rolling
  the check; `shell/sidebar-icon-policy.html` and `search/boost.html` are the
  reference call sites. Reach for `warnidf` when a site should be able to
  accept a known warning via `ignoreLogs`.
  Two facts make this safe, and both must stay true: one `errorf` aborts the
  *whole* build, so in `hugo server` a single author's typo serves HTTP 500 on
  every URL of the site, not just the broken page; and every gate that
  publishes anything builds with `--panicOnWarning` (`ci.yml`,
  `bin/sites/build-all.py`, the site repo's `pages.yml`), so a warning is
  still a hard failure everywhere it counts. Warning is strictly better than
  erroring: same enforcement at the gates, no shared preview outage.
  Protection comes from refusing to emit bad output, not from halting — an
  unsafe CSS length falls back to the default, a diagram without its server
  URL renders nothing, and neither needs to take the site down. Render hooks
  share one attribute policy (`content/attributes.html`): allowlisted keys are
  consumed, `class` (token-validated), `data-*`, and `aria-*` pass through;
  `style`/`on*` and unknown keys warn and are dropped.
- Public string parameters (captions, labels, titles) are plain text; only
  Markdown *bodies* (tab, card, field, image caption, Book bodies) are Markdown.
  Those bodies render as their own Goldmark document, so a footnote reference
  in one fails the build: footnotes are page-level, and a numbered table or
  fence that needs them uses the native `{num=… caption=…}` form.
- Icons are one Font Awesome class pair (`fa-solid fa-rocket`); no icon
  registry, no `oink-` prefixes — theme-generated classes stay `td-`, author
  markers are unprefixed.
- CSS must handle `forced-colors`, reduced motion, print, and RTL (use logical
  properties).

## Conventions

- **No `oink.*` config tree, no `oink.enabled` switch, no parallel visual
  shell.** The standard layouts are the product; upstream Docsy changes are
  ported into the single canonical implementation rather than gated behind a
  brand switch.
- Theme parameters live under `params.ui.*` in `hugo.yaml`; theme defaults there
  are intentionally conservative — interactive features (`offline_search`,
  `ui.image_zoom`, `comments`, `ui.feedback`) are opt-in so
  the theme never sets site policy. Every default is declared there with its
  value range in a comment (only `ui.quick_links` and `ui.taxonomy_icons` are
  derived), and the template `| default` fallbacks match the declared values.
- Parameter shapes (`check-params.py`): a boolean switch is the bare feature
  name (`ui.annotation: true`, no `.enable`, no `_enabled` unless a sibling
  family forces it); single-key maps are flattened; a map survives only for a
  feature with several settings and also accepts a bare boolean; a front
  matter override is the site key without `ui.`; keys are snake_case except
  values passed straight to an external runtime (`comments.giscus.*`,
  `mermaid.*`). Renaming a key means adding it to `config-legacy.html` /
  `front-matter-legacy.html` (build fails, error names the new key) and to the
  matrix in `check-params.py`, in the same commit.
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
