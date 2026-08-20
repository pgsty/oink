---
title: 'OINK implementation diary: from copied shells to one theme'
linkTitle: OINK implementation diary
date: 2026-08-08
aliases: [/blog/2026/oink-implementation-diary/]
lastmod: 2026-08-08
description: >-
  A technical diary of the decisions, migrations, safety boundaries, tests, and
  documentation work behind the OINK implementation preview.
author: OINK maintainers
tags: [Oink]
---

OINK began with an awkward observation: several production documentation sites
looked related because they were related, but their common implementation lived
as copied files. The visible result was consistent enough; the maintenance model
was not.

This diary records how the project moved from repeated site overrides to one
directly evolved theme. It focuses on decisions and evidence rather than a
commit-by-commit transcript.

## Locking the contract

The first useful work was subtraction. We wrote down what the product must be
before choosing how to implement it:

- an independent theme derived directly from Docsy;
- one canonical shell, not a switchable skin;
- Hugo Extended as the only consumer build dependency;
- local-first delivery for every theme-owned browser asset;
- multilingual behavior derived from Hugo rather than PGSTY domains;
- reusable components in the theme, business semantics in the site;
- preserved Docsy history, licenses, and upstream traceability.

This ruled out an attractive but costly shortcut: adding `params.oink.enabled`
and leaving the old shell in place. A mode switch would have made every layout
change, accessibility fix, and test support two products. Direct evolution made
the intended design the only design.

## Replacing the shell

The documentation, blog, and API-reference layouts were rebuilt around shared,
small partials. The resulting shell includes:

- global navigation and responsive sub-navigation;
- a resizable, foldable sidebar;
- local search and quick links;
- language and color-mode controls;
- breadcrumbs, table of contents, page metadata, and feedback;
- a consistent footer and print layout.

The hard part was not drawing a navbar. It was preserving existing Docsy
extension points while removing copied `baseof.html` files. Narrow hooks remain;
site-wide shell duplication no longer has to be the normal customization path.

## Removing the consumer toolchain

The original dependency chain assumed npm-provided Bootstrap and Font Awesome,
and some paths invoked PostCSS. OINK moved the required sources and compiled
artifacts into the theme and kept SCSS inside Hugo's own asset pipeline.

Tests do more than check that `hugo` succeeds. Fixture traps fail if a consumer
build tries to run Node.js, npm, PostCSS, or Autoprefixer, or if a template uses
`resources.GetRemote`. LTR and RTL pages go through the same constraint.

This distinction matters: the repository still uses Node for its maintainer test
harness. "Hugo-only" describes what a consuming site needs after it has a
complete theme, not a ban on development tooling inside the theme repository.

## Vendoring browser runtimes

The next layer was every dependency the browser might otherwise fetch:
Bootstrap, Font Awesome, fonts, jQuery, Lunr, Mermaid, KaTeX, Markmap, Swagger
UI, Redoc, Asciinema, ECharts, Infographic, and their supporting libraries.

Each selected artifact received a source, fixed version, license path, checksum,
and update procedure in `theme/VENDOR.json`. Licenses live beside the vendored
material. The manifest is validated against the actual files rather than treated
as an aspirational inventory.

PlantUML and Diagrams.net forced a useful distinction. They are service-backed
features, not merely JavaScript libraries. OINK refuses to invent a public
endpoint: enabling one without a configured service fails the build.

## Building the multilingual core

The previous language behavior was scattered across navigation and site-specific
assumptions. The new core starts with Hugo's configured languages,
`.Translations`, and `.AllTranslations`.

The presentation is deliberately stable: one language hides the selector; two or
more use the same icon button. Clicking advances by configured weight, while a
short hover or keyboard focus opens the complete language menu.

A missing translation falls back to the target-language home page. Language
labels use each language's own name. The same objects drive `lang`, direction,
canonical, `hreflang`, and Open Graph locale metadata, so the visible selector
cannot drift from SEO output.

The tests construct every state with an RTL current language as well as normal
LTR cases. Native links and disclosure controls keep keyboard behavior
predictable.

## Promoting components

Asciinema, ECharts, Infographic, document carousel, details, tabs, cards, and
parameter rendering had already proved valuable in PGSTY sites. The work was to
turn them from copies into product APIs:

- normalize parameter names and defaults;
- generate unique IDs from page identity and shortcode ordinal;
- load each runtime once per page and omit it from unused pages;
- preserve subpath URLs;
- support repeated identical instances;
- provide print, dark-mode, mobile, keyboard, and reduced-motion behavior;
- retain compatible aliases for imported content.

Product matrices and other business widgets did not move. Reuse is not measured
by the number of repositories containing a copy; it requires a stable,
business-neutral contract.

## Supporting ECharts callbacks {#designing-safe-echarts}

ECharts callbacks are legitimate chart options that JSON and YAML cannot
express. Existing pages use them for tooltip formatting, label formatting, and
data-dependent colors. Treating those callbacks as a separate migration
exception added configuration without creating a sandbox.

The shortcode therefore keeps one direct contract:

1. content supplies JSON or YAML, which Hugo parses and safely serializes;
2. an optional fenced JavaScript block declares callbacks;
3. `$fn:name` values reconnect those callbacks after the options are parsed;
4. authors review executable code under the same trust model as inline HTML and
   other custom integrations.

Tests cover repeated identical charts, invalid CSS lengths, structured options,
and callback registration.

## Creating the starter and archive

A contract is easier to trust when the smallest example demonstrates it. The
starter contains bilingual home, docs, blog, and component pages; local search;
dark mode; diagrams; API documentation; and the new components. It has no
`package.json` and no site workflow.

The offline packager combines `theme/`, `starter/`, licenses, the upstream
record, and migration guidance, excluding generated output and dependency
caches. It writes a sidecar SHA-256 file and refuses to overwrite an existing
artifact.

The acceptance test copies the starter and theme to a temporary directory,
empties caches, blocks HTTP/HTTPS and Go proxies, builds with Hugo, and examines
HTML and CSS for third-party subresources.

## Rehearsing four migrations

SILO, PGSTY, SOW, and Pigsty provided the reality check. The rehearsal tool
copies each workspace instead of modifying it, removes only classified common
overrides, applies a local theme replacement, forbids network and frontend
tools, and runs the production build.

The latest rehearsal removed 20 common overrides from SILO, PGSTY, and SOW and
24 from Pigsty. Pigsty retained its three business matrix shortcodes and
existing ECharts callbacks. All temporary copies built, producing 1,095, 16,
128, and 2,473 HTML files respectively.

Those numbers prove the rehearsal at the recorded commits. They do not prove
that any production repository was changed or any hosted site was deployed.

## Turning the sample into OINK docs

The inherited `docsy.dev` site was valuable as a regression corpus, but it
described only Docsy. The documentation phase did four things:

1. made English primary and Simplified Chinese second; a later shell review
   removed French from the demonstration site;
2. translated every core documentation and blog source into a colocated `.zh.md`
   page;
3. preserved English heading IDs explicitly in every Chinese heading;
4. added the OINK product guide, announcement, and this implementation diary.

Before translation, we established a terminology and typography guide. A checker
then verifies source/translation pairs, heading counts, explicit Chinese IDs,
and rendered English/Chinese heading-ID equality.

Historical Docsy release posts remain faithful translations. Their npm-era
instructions are historical context, while the OINK architecture and migration
guides state the current Hugo-only product contract.

## What testing changed

Several tests changed the design rather than merely blessing it:

- subpath fixtures forced every local component URL through Hugo URL handling;
- repeated-instance tests replaced content hashes with page-and-ordinal IDs;
- offline browser checks exposed implicit runtime requests;
- RTL language matrices prevented a selector implementation that only worked for
  the starter's two LTR languages;
- ECharts callback fixtures kept callback registration and structured options
  interoperable;
- migration rehearsals preserved site-specific partials that a blanket
  `layouts/` deletion would have removed.

The strongest test suite is one that constrains the product boundary, not just
the current HTML snapshot.

## Remaining work

Two release gates remain intentionally open. The public brand, repository,
module and package identities, and first version need approval. A real
Cloudflare Pages project then needs to build from the source branch and pass
hosted verification.

Production migrations should proceed one site at a time, with dedicated
branches, preview deployments, visual regression, and rollback artifacts. The
temporary four-site rehearsal is a foundation for that work, not a substitute.

## Lessons

- Write the product boundary before moving files.
- A local-first promise needs both build-time and browser-time evidence.
- Configuration is healthier when it expresses user choices, not internal
  implementation branches.
- Translation quality includes stable links, code fidelity, typography, and
  rendered structure—not prose alone.
- Reuse should remove maintenance copies without absorbing business semantics.
- "Built," "packaged," "published," "deployed," and "migrated" are different
  claims and need different evidence.

The result is less dramatic than a rewrite and more useful: one theme that can
be understood, built, tested, translated, and migrated as a coherent product.
