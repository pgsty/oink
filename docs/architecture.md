# Architecture contract

## Repository and assembly

The repository root is a Hugo Module and complete theme, not a site or npm
workspace. Hugo Extended compiles SCSS and templates. Browser runtimes and
third-party assets are committed, so a normal build performs no network fetch.
`tests/site/` is the self-contained internal fixture for theme checks and
goldens. Public documentation, examples, and browser tests live in the sibling
`oink.pgsty.com` repository.

Generated `public/` and `resources/` trees are never source. Vendored runtimes,
font families, and Font Awesome glyph definitions are supported distributions,
not dead-code candidates; `VENDOR.json` and `bin/check-vendor.py` pin their
integrity. OINK ships the complete supported Font Awesome distribution because
consumer-authored content may use icons that theme templates do not.

Hugo types `docs`, `book`, `blog`, and `swagger` select the reading shells;
`params.ui.shell_types` may add types. Landing is `layout: landing`. There is no
`article` type or second blog shell: immersive pages are a blog presentation
described in [shell.md](shell.md).

`layouts/_partials/shell/config.html` resolves shared shell facts. Layouts must
render through `content/render.html` before `scripts.html`, because render hooks
and shortcodes register capability flags in the Page Store. Override the
narrowest partial; superficially similar base templates remain separate where
merging would change Hugo lookup precedence.

## Configuration and diagnostics

Theme policy lives under `params.ui.*`; multi-setting integrations such as
`comments.giscus`, `plantuml`, and `drawio` stay top-level. Boolean features use
bare booleans unless they also have several settings. A page override drops the
`ui.` prefix: `params.ui.image_zoom` becomes `image_zoom`, never a front-matter
`ui` map. `hugo.yaml` declares published defaults; an owning resolver and its
checker define any optional configuration shape or range.

Invalid input follows one rule: warn with the value, allowed shape, and safe
fallback; then use that fallback or omit the unsafe feature. Ordinary
`hugo server` therefore remains usable, while every publishing gate uses
`--panicOnWarning`. The theme never calls `errorf`, and `check-params.py`
enforces that boundary. Do not add speculative validation for unreachable
states.

There is no generic renamed-key registry. A transition that still needs a
migration diagnostic uses a targeted warning in its owning resolver plus a
strict negative test; removed keys are never read as a compatibility path.

Network-capable features are explicit and degrade closed. PlantUML requires
`plantuml.svg_image_url`, Draw.io requires `drawio.drawio_server`, and Algolia
requires `appId`, `apiKey`, and `indexName`; incomplete configuration warns and
emits no request. Draw.io loads only when rendered content contains PNG or SVG
candidates, then inspects each distinct image URL once.

## Featured images

Hugo's `images` is the single authored API; `params.images` is only the
site-wide social fallback.

| Source | Reader thumbnail | Social card |
| --- | --- | --- |
| Page `images`, or bundled `**featured*`, `*feature*`, `{*cover*,*thumbnail*}` | yes | yes |
| Section `cascade.images` | yes | yes |
| Site `params.images` | no | yes |

`images: []` clears an explicit or cascaded value but does not disable bundled
resource discovery. Only the first resolved image is representative. Local
processable rasters may be cropped; SVG, static, and remote resources remain
valid without Hugo image operations.

`featured-image-resolve.html` owns source ranking and relative/absolute URLs.
A page's bundled resource outranks an inherited cascade image. List thumbnails,
Open Graph/Twitter/schema helpers, author avatars, Pinterest media, and blog
presentation all consume that decision.

`params.ui.featured_image` is blog-only and defaults to `none`; front matter
overrides it per page or cascade. `banner` renders a figure above a single-page
title, `wash` colors its header, and `hero` paints the shell backdrop on single
pages and section indexes. Missing images and non-HTML output render no image.

## Outputs and runtime

Every base template sets `Page.Store.tdOutputFormat`:

| Output | Contract |
| --- | --- |
| HTML | Complete semantic content; local runtime only for used capabilities |
| Print | Expanded content; no shell navigation, search, or zoom runtime; the shared action layer supports explicit print controls |
| Markdown / LLMS | Source-shaped Markdown without `td-` component markup |
| RSS | Safe static summary or explicit omission |

Consumers opt into custom outputs; OINK does not force expensive Book
aggregates. HTML gets the shared action and core layers plus a feature bundle
keyed by actual page capabilities and language. Print keeps the action layer and
only runtimes required by rendered print features. Large third-party UMD files
stay separate; unused feature runtimes stay absent.

Performance rules:

- do not walk `.Site.Pages` per page when a site-level resource or
  `partialCached` result can own the work;
- render `.Content` once and read Page Store flags only after it;
- emit correct markup instead of scanning the DOM to repair it;
- group browser work by resource URL, not DOM instance;
- keep ordinary outputs opt-in when their aggregate cost is material;
- validate reachable author input, not hypothetical internal states.

`bin/measure-baseline.py` measures build time, output weight, bundle count, and
shortcode density. `bin/sites/build-all.py` builds maintained consumers in
isolated snapshots.

## Trust, CSS, and accessibility

Authors may enable Goldmark `unsafe`; configuration and component parameters
are not raw HTML. The shared attribute policy consumes an allowlist, validates
class tokens, passes `data-*` and `aria-*`, and warns while dropping `style`,
`srcdoc`, `on*`, reserved, and unknown attributes. URL helpers reject dangerous
schemes and protocol-relative URLs where local or explicit absolute URLs are
required. Promised remote URLs remain supported but are never fetched at build
time.

Theme output uses `td-` classes, `data-td-*` attributes, and `--td-*` custom
properties; author markers such as `.steps`, `.cards`, and `.full-width` stay
unprefixed. CSS supports RTL, print, forced colors, reduced motion, long tokens,
and narrow viewports. Theme-owned decorative icons carry `aria-hidden`; pages
with task lists or raw authored Font Awesome elements alone load the authored
accessibility repair.

Font roles are `ui`, `body`, `heading`, `code`, `display`, `metadata`, and
`print`, exposed as `--td-*-font-family`. `params.ui.typography` is `technical`
or `system`; both compile into one stylesheet with no runtime. Legacy
Bootstrap/Docsy Sass variables continue to seed these roles.

## Release states

Source complete, locally validated, committed, tagged, pushed, pinned by a
consumer, deployed, and production-identical are distinct states. A local Hugo
build proves only local validation.
