# Architecture contract

Status: current for OINK 0.5.0
Compatibility floor: Hugo Extended 0.160.1

## Repository and build

The repository root is a Hugo Module and a complete theme, not a site or an npm
workspace. Hugo Extended compiles SCSS and templates. All browser runtimes and
third-party assets are committed; a normal build performs no network fetch.
`exampleSite/` is the small CI fixture. The bilingual product documentation and
browser suite live in the sibling `oink.pgsty.com` repository.

Generated `public/` and `resources/` trees are never source. Vendored files in
`assets/third_party/`, Font Awesome glyph definitions, and font families are
distributions rather than dead-code candidates; their integrity is checked by
`bin/check-vendor.py`.

## Template assembly

Hugo type selects the reading shell. `docs`, `book`, `blog`, and `swagger` are
the defaults; `params.ui.shell_types` may add types. Paths only identify the
configured navigation roots.

`layouts/_partials/shell/config.html` resolves shared shell facts. Page layouts
render content before `layouts/_partials/scripts.html`, because render hooks and
shortcodes register feature flags in the Page Store. A new layout must use
`content/render.html` rather than render `.Content` independently.

Override the narrowest partial. Consumer overrides are part of the Hugo Module
contract, so identical-looking base templates are not merged when doing so
would change Hugo lookup precedence.

## Configuration

Theme policy lives under `params.ui.*`; feature-specific maps such as
`comments.giscus`, `plantuml`, and `drawio` remain top-level. A boolean feature
uses a bare boolean unless it has several settings. Page overrides use the site
key without `ui.`: `params.ui.image_zoom` becomes front matter `image_zoom`.
Front matter never contains a `ui` map.

`hugo.yaml` declares every default. `config-legacy.html` and
`front-matter-legacy.html` fail on renamed keys and name the replacement. They
are a migration boundary, not a second resolver.

Network-capable features are explicit and fail closed. PlantUML requires
`plantuml.svg_image_url`, Draw.io requires `drawio.drawio_server`, and Algolia
requires `appId`, `apiKey`, and `indexName`.

When Draw.io is enabled, `scripts.html` emits `#td-drawio-config` before the
feature bundle. The runtime reads the configured server from that JSON element
at DOM ready and remains inactive if a consumer override omits the element.

## Featured images

The theme invents no key here. Hugo's `images` carries a featured image at
every level, and `params.images` is the site-wide social card.

| Level | Written as | Renders as a thumbnail | Shared as a card |
| --- | --- | --- | --- |
| Page | `images: [<path>]`, or a bundled `**featured*` / `*feature*` / `{*cover*,*thumbnail*}` resource | yes | yes |
| Directory | `cascade: { images: [<path>] }` on the section `_index.md` | yes | yes |
| Site | `params.images` | no | yes |

`images: []` opts a page out; the same on a `cascade` opts a whole section out.
Either way the site card still applies, because declining a thumbnail is not
declining a card.

`featured-image-resolve.html` is the only place that decides, and it ranks a
bundled resource above `images` inherited from a cascade: Hugo merges a cascade
into `.Params`, so the two are told apart by comparing with the nearest ancestor
carrying the key. Without that, a directory default would outrank a post's own
bundled image.

Three consumers share the decision, so what a reader sees and what a social card
carries cannot drift apart: `featured-image.html` and `shell/blog-row.html`
render it, and `_funcs/get-page-images.html` -- the theme's override of the
helper behind Hugo's `opengraph.html`, `twitter_cards.html`, and `schema.html`
-- hands it to the metadata templates. Those templates themselves stay Hugo's.

The resolver also owns the URL work, because Hugo and the theme disagree about a
leading slash: Hugo resolves it against the host, the theme against the site. A
configured value reaches the shared image URL policy, resolves against page and
global resources, and comes back in both relative and absolute form.
`images-param.html` reads the parameter as a list whether a site wrote one.

## Output formats

Every base template sets `Page.Store.tdOutputFormat` to `html`, `print`,
`markdown`, or `rss`. Components branch on this value:

| Output | Contract |
| --- | --- |
| HTML | Semantic static content first; local runtime only for used capabilities |
| Print | Expanded static content; no drawers, copy buttons, zoom, or search runtime |
| Markdown / LLMS | Source-shaped Markdown without theme classes |
| RSS | Safe static summary or explicit omission where a component has no useful feed form |

Consuming sites opt into custom outputs. The theme does not force `print`,
`markdown`, or `LLMS` because aggregate Book output can be expensive.

## Runtime loading and performance

`scripts.html` emits three layers:

1. a small action bundle used by HTML and print controls;
2. one cache-stable interactive core bundle;
3. a page feature bundle derived from its actual resource members and language.

Large third-party UMD files remain separate so feature combinations do not
duplicate them. Page Store flags are write-only during content rendering and
read only after content is complete. A page that does not use a feature must
not receive its runtime.

Performance rules:

- do not walk `.Site.Pages` from a per-page partial when a site-level resource
  or `partialCached` result can own the work;
- do not render `.Content` twice;
- do not scan the whole DOM to repair markup the theme can emit correctly;
- group browser work by resource URL instead of repeating it per DOM instance;
- keep feature validation at build time, but do not add speculative checks on
  unreachable states;
- measure large aggregate outputs explicitly rather than enabling them by
  default.

`bin/measure-baseline.py` measures build time, output weight, bundle count,
and shortcode density. `bin/sites/build-all.py` builds the maintained site
corpus in isolated snapshots.

## Content trust boundary

Authors are trusted to enable Goldmark `unsafe`; configuration and reusable
component parameters are not trusted as raw HTML. The shared attribute policy:

- consumes a component-specific allowlist;
- validates `class` as tokens;
- passes `data-*` and `aria-*`;
- rejects `style`, `on*`, `srcdoc`, and unknown keys.

The URL resolver rejects dangerous schemes and protocol-relative URLs where a
local or explicit absolute URL is required. Remote URLs remain supported where
the public API promises them; the theme does not fetch them during builds.

## CSS, accessibility, and typography

Theme output uses `td-` classes, `data-td-*` attributes, and `--td-*` custom
properties. Author markers such as `.steps`, `.cards`, and `.full-width` are
deliberately unprefixed. CSS must handle RTL, print, forced colors, reduced
motion, long unbroken content, and narrow viewports.

Theme-generated Font Awesome elements are decorative unless they are the only
content of a named control; decorative icons carry `aria-hidden="true"` in the
template. The theme ships the complete supported icon distribution rather than
pruning glyphs based on its own templates.

Pages containing Goldmark task lists or raw authored Font Awesome elements
load `authored-a11y.js`; other pages omit that repair runtime.

Semantic font roles are `ui`, `body`, `heading`, `code`, `display`, `metadata`,
and `print`, exposed as `--td-*-font-family`. `params.ui.typography` is
`technical` (default) or `system`. Both compile into the same stylesheet and
load no runtime. Legacy Bootstrap/Docsy Sass font variables seed the roles so
consumer overrides continue to work.

## Release states

Source complete, locally validated, committed, tagged, pushed, pinned by a
consumer, deployed, and production-identical are separate states. A local Hugo
build establishes only local validation.
