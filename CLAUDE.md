# CLAUDE.md

Guidance for working in `github.com/pgsty/oink`.

## Repository boundary

This repository is the OINK Hugo Module: layouts, partials, shortcodes, SCSS,
browser JS, i18n, vendored assets, defaults, migration tools, and theme checks. The
root is the module; there is no site, npm workspace, or generated build input.
Hugo Extended is the build tool.

The sibling `../oink.pgsty.com` repository owns the public bilingual product
documentation, tutorials, examples, case studies, Node/Playwright regression
tests, visual review, and deployment. Active theme-maintainer contracts stay
compact under this repository's `docs/` directory. Do not recreate
`exampleSite/` or parallel proposal/design trees.

This repository keeps a self-contained synthetic fixture under `tests/site/`
for focused checkers, invalid-input cases, and output goldens. It is not a
public example, integration-test authority, or visual approval surface. The
public site pins a released OINK tag; local cross-repo validation uses an inline
`HUGO_MODULE_REPLACEMENTS` for that command. Never commit a filesystem replace.

`main` is the next-release branch; `release` is current stable. Immutable
`vX.Y.Z` tags count as published only after push and Go-proxy verification.

## Shortest commands

Run the narrow checker that owns a change; `.github/workflows/ci.yml` is the
complete ordered theme-unit suite. Then run integration, browser, accessibility,
responsive, and visual validation against the sibling documentation site.

```sh
python3 bin/check-shell.py               # shell, blog, page-end contracts
python3 bin/check-components.py          # component and render-hook contracts
python3 bin/check-output.py              # rendered structure/runtime/security
python3 bin/check-goldens.py             # HTML/print/Markdown/RSS/LLMS goldens
python3 bin/check-params.py              # config shapes and warning fallbacks
python3 bin/check-i18n.py                 # locale schema parity
node --test 'tests/js/**/*.test.js'       # browser-runtime units
hugo --source tests/site --printPathWarnings --panicOnWarning
```

From `../oink.pgsty.com`, validate and preview the real bilingual site with the
current theme checkout:

```sh
HUGO_MODULE_REPLACEMENTS='github.com/pgsty/oink -> /Users/vonng/pgsty/oink' npm test
HUGO_MODULE_REPLACEMENTS='github.com/pgsty/oink -> /Users/vonng/pgsty/oink' npm run test:browser
HUGO_MODULE_REPLACEMENTS='github.com/pgsty/oink -> /Users/vonng/pgsty/oink' hugo server -DFE
```

Migration is dry-run unless `--write` is explicit:

```sh
python3 bin/migrations/oink06.py report --sites <dir>...
python3 bin/migrations/oink06.py migrate --site <dir> [--write]
python3 bin/migrations/oink06.py check --site <dir>
python3 -m unittest discover -s tests/migrations -t .
```

The toolkit rewrites only content Markdown and supported YAML front matter. It
does not edit site configuration, data, layouts, assets, or modules.

Use Hugo Extended 0.160.1 for the compatibility floor. Output checkers accept
`--hugo` and `--public`; reuse a build only when that is the narrowest proof.
`check-goldens.py --update` is an intentional behavior change, never cleanup.

## Non-negotiable contracts

- The current 0.6.0 draft contracts are indexed by `docs/README.md`. History
  belongs in Git and `CHANGELOG.md`, not parallel proposal documents.
- Reading shells are `docs`, `book`, `blog`, and `swagger`, plus explicit
  `params.ui.shell_types`. Landing is a layout. Immersive reading is the
  ordinary blog shell with hero/TOC-flow/clouds/sidebar keys, never an
  `article` type or second shell. The blog shell defaults its breadcrumb off;
  `breadcrumb` stays an ordinary key.
- Render content once through `content/render.html` before `scripts.html`.
  Shortcodes and hooks set Page Store capability flags; bundle assembly reads
  them afterwards. Add each new runtime flag to the bundle key.
- HTML is semantic-first and progressively enhanced. Print is static and
  expanded; Markdown/LLMS contains no component markup; RSS is safe static
  output or explicit omission. Consumers opt into expensive custom outputs.
- Invalid author/config input warns, uses a documented safe fallback or emits
  nothing, and keeps ordinary `hugo server` usable. Publishing gates use
  `--panicOnWarning`. Never call `errorf` or add speculative validation for
  unreachable internal states.
- Theme policy lives under `params.ui.*`; page overrides drop `ui.`. Boolean
  switches are bare booleans unless a multi-setting feature also accepts a
  boolean shorthand. Public renames get a targeted owning-resolver warning,
  migration note, and strict negative test—not a global compatibility registry.
- Theme-owned network features are off until explicitly and completely
  configured. A normal build downloads nothing. Vendored artifact, license,
  version, and checksum change together in `VENDOR.json`.
- Do not prune vendored fonts or Font Awesome by apparent template usage. The
  complete supported distribution is public authoring surface.
- Shortcode and component labels are plain text; Landing narrative fields may
  render Markdown. Icons are one Font Awesome class pair. Shared attribute and
  URL policies drop unsafe output rather than repairing it in the browser.
- CSS uses `td-` classes, `data-td-*`, `--td-*`, logical properties, and covers
  RTL, print, forced colors, reduced motion, narrow screens, and long tokens.
  Author markers such as `.steps` and `.cards` remain unprefixed.
- Keep all 32 locale files schema-identical. Add user-visible strings to every
  locale; `bin/check-i18n.py --sync` may add mechanical English fallbacks.
- Override the narrowest partial. Do not merge base templates when that changes
  Hugo lookup precedence or copy a full shell for one feature.
- `public/` and `resources/` are generated and ignored. Never commit them.

The public surface is 29 shortcodes, 22 Landing sections, shared output and
security rules, and the blog hero/index/authors/series/share contracts. Their
single maintainer references are indexed by `docs/README.md`.

## Release status

Report states precisely:

source complete → locally validated → committed → tagged → pushed/proxy
verified → consumer pinned → deployed → production-identical.

A green local build proves only local validation. Tags are never moved; a
published mistake receives a new patch release.
