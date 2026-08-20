---
title: Introducing the OINK implementation preview
linkTitle: Introducing OINK
date: 2026-08-08
aliases: [/blog/2026/oink-announcement/]
lastmod: 2026-08-08
description: >-
  OINK turns a directly customized Docsy codebase into a local-first, Hugo-only
  documentation theme with multilingual infrastructure and reusable content
  components.
authors: [oink, vonng]
featured_image: wash
tags: [Oink]
---

Today we are publishing the OINK implementation preview: a directly evolved
Docsy theme with one canonical product shell, a Hugo-only consumer build,
local-first browser dependencies, a general multilingual framework, and a set of
reusable content components drawn from PGSTY documentation sites.

This is an implementation and documentation milestone, not a public versioned
release. The final public brand, module and package identities, first version,
and production Cloudflare Pages deployment remain explicit release gates.

## Why OINK exists

Several mature documentation sites had independently copied the same Docsy
layouts, navigation, search code, SCSS, JavaScript, and shortcodes. A common fix
had to be repeated across repositories, while each site also carried a frontend
toolchain and implicit network dependencies that made isolated builds harder
than they needed to be.

OINK consolidates the genuinely reusable layer. Product matrices, portals,
pricing pages, and other business-specific behavior stay in their own sites. The
shared theme owns the documentation shell, browser runtimes, multilingual
routing, accessibility behavior, and content-component contracts.

## What changes

### One product instead of a mode

OINK is not an optional skin. There is no `oink.enabled` flag, `params.oink.*`
namespace, or parallel upstream-versus-brand template tree. The implementation
in `theme/` is the product.

That decision avoids two visual systems and two test matrices. Native Hugo
settings and compatible Docsy parameters keep their established meanings.

### Hugo-only consumer builds

A complete consuming site builds with:

```sh
hugo --gc --minify
```

Bootstrap, Font Awesome, fonts, search, diagrams, API documentation runtimes,
and OINK components are committed with the theme. Node.js, npm, PostCSS,
Autoprefixer, and CDN downloads are not consumer requirements.

Repository maintainers still use Node-based tools for tests and vendor
refreshes. That maintenance toolchain is deliberately outside the public
site-build contract.

### Local-first browser behavior

The default starter serves its shell, fonts, icons, search, Mermaid, KaTeX,
Markmap, Swagger UI, Redoc, Asciinema, ECharts, and Infographic dependencies
from the generated site. Optional runtimes are selected per page and loaded at
most once.

PlantUML and Diagrams.net do not receive public service defaults. A site must
configure a controlled endpoint, use a pre-rendered result, or make an explicit
remote-service choice.

### Multilingual infrastructure

Language routing comes from Hugo's language and translation objects. One
configured language hides the selector. With two or more languages, a click
advances by configured weight, while a short hover or keyboard focus opens the
complete menu. If the current page lacks a translation, the selector goes to the
target-language home page instead of a dead path.

The starter and documentation site use English as the primary language and
Simplified Chinese as the second. Every page in the core docs and blog scope has
a colocated `.zh.md` translation with stable explicit heading IDs.

### Reusable components

OINK adds theme-owned Asciinema, ECharts, Infographic, document carousel,
details, tabs, cards, navigation cards, document cards, and parameter
components. They generate unique instance IDs and load their local assets only
when used.

ECharts accepts structured JSON or YAML plus optional JavaScript callbacks
referenced as `$fn:name`. Callback code runs only on pages that declare it.

## What stays familiar

OINK retains Docsy's content organization, front matter, documentation and blog
sections, menus, taxonomies, print output, repository links, common shortcodes,
diagrams, API reference features, and extension hooks. Existing sites can remove
duplicated common implementations without rewriting ordinary Markdown.

The project also preserves Docsy's Apache-2.0 history and attribution. A vendor
manifest records pinned third-party sources, licenses, artifacts, and checksums.

## Try the starter

Install Hugo Extended `0.160.1` or newer, then run from this checkout:

```sh
hugo --source starter --gc --minify
```

The current validation baseline is Hugo Extended `0.164.0`. Open the generated
English and Chinese pages, switch languages, search locally, change color mode,
and visit the component examples.

For a network-isolated transfer, maintainers can create a complete archive:

```sh
scripts/package-offline.sh /absolute/path/oink-preview.tar.gz preview
```

The archive includes the theme, starter, licenses, upstream record, migration
guide, vendor manifest, and a sidecar checksum.

## Current validation

The implementation includes automated coverage for:

- minimum-version and current Hugo Extended builds;
- forbidden consumer Node/npm/PostCSS/Autoprefixer paths;
- LTR, RTL, subpath, print, color-mode, and production assets;
- hidden, click-to-cycle, hover-menu, translation-fallback, and RTL language
  behavior;
- local per-page runtimes and repeated component instances;
- ECharts structured options and callback integration;
- an offline bilingual starter and offline release archive;
- vendor licenses and checksums;
- non-mutating migration rehearsals for SILO, PGSTY, SOW, and Pigsty.

The latest four-site rehearsal built temporary copies successfully. It did not
modify or deploy those production repositories.

## What remains before release

The public identity and first version must be approved and applied consistently
to the module, package, source tags, nested theme tag, archive, and
documentation. The target Cloudflare Pages project must then be connected to the
source branch, built with the pinned Hugo version, published, and verified at
its hosted URL.

Until those gates close, use the preview for evaluation and migration rehearsal,
not as an unversioned production dependency.

## Read next

- [OINK overview](/docs/about/)
- [Architecture](/docs/about/architecture/)
- [Local-first operation](/docs/about/local-first/)
- [Content components](/docs/components/)
- [Configuration](/docs/customize/config/)
- [Migration guide](/docs/upgrade/from-docsy/)
- [Release process](/docs/about/)
- [Implementation diary](/blog/oink/oink-implementation-diary/)
