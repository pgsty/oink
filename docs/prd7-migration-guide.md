# PRD 7 shell and page-end migration guide

This guide covers the navigation, responsive shell, search-preview, and
page-end changes introduced after OINK 0.4.1. The compatibility floor remains
Hugo Extended 0.160.1.

[简体中文](prd7-migration-guide.zh.md)

## 1. Upgrade the configuration

OINK feedback is now a one-click, structured client-side interaction. Remove
legacy or prototype fields such as `yes`, `no`, `max_value`, `endpoint`, and
`max_length`; a Worker or form-submission endpoint is not part of the standard
flow.

```yaml
params:
  offlineSearch: true
  # Keep large local previews fast. Opt in only while testing search.
  offlineSearchOnServe: false
  ui:
    navbar_autohide: false
    annotation:
      enable: true
    pager:
      types: [docs, book, blog]
    feedback:
      enable: false
      reasons: true
    sidebar_root_menu: true
```

For a documentation section, enable feedback with a cascade while leaving Blog
discussion-only:

```yaml
# content/docs/_index.md
cascade:
  type: docs
  feedback: true
  comments: true
  navbar_autohide: true
  footer_style: slim
```

```yaml
# content/blog/_index.md
cascade:
  type: blog
  feedback: false
  comments: true
  navbar_autohide: true
  footer_style: slim
```

Page-level `feedback`, `annotation`, `comments`, and `navbar_autohide` values
override the inherited policy. These switches must be booleans. Pager keeps
the established PRD 5 contract: `params.ui.pager.types` selects the enabled
content types, while page or cascaded `pager: false` opts a page out.
`params.ui.feedback.reasons: false` keeps the two primary choices but hides the
optional reason chips.

## 2. Analytics and comments are separate

When a global `gtag` function exists, a primary choice emits:

```text
docs_feedback { result, page_path, language }
```

An optional reason emits a second event with `reason` and
`refinement: true`. Without analytics, the UI still completes and remembers
the fixed choice locally. OINK sends no free text and makes no feedback network
request.

If Giscus is configured and active on the page, the result links to the same
page's comment section for details. OINK does not post into Giscus, create a
GitHub App identity, or treat the Giscus iframe as a form API.

## 3. Preserve consumer overrides

Every Docs, Book, Swagger, and Blog reading template now calls
`layouts/_partials/page-end.html` in this order:

1. Feedback
2. Annotation
3. Previous/Next pager
4. Comments

The default Annotation slot continues to call
`page-meta-lastmod.html`, so an existing consumer override remains compatible.
Sites that need provenance or translation metadata may instead override
`page-annotation.html`; do not copy the whole content template just to change
the annotation.

The pager follows the rendered sidebar order for Docs, Book, and Blog,
including each root landing. Explicitly weighted Blog pages come first;
unweighted pages follow in reverse chronological order.

## 4. Navigation and responsive behavior

With `params.ui.sidebar_root_menu: true`, the section switcher contains
top-level sections plus `sidebar_root_for: self` roots. A top-level section can
opt out with `sidebar_root_menu: false`. The current root remains the first
selectable sidebar and pager entry. A self-root now links to its own landing by
default; a site that intentionally used the historical parent-link behavior
can preserve it explicitly with `sidebar_root_link_self: false` on that root.

A main-menu item targeting a Hugo taxonomy page, including a legacy URL-based
entry such as `/tags/`, gains a count-sorted term panel on desktop. Mobile
menus keep the parent taxonomy link instead of rendering the full term cloud.

`params.ui.navbar_autohide: true` affects fine-pointer viewports at 768px and
above. Touch devices and the complete drawer-width tier keep the navbar
visible. The mobile drawer retains search, section switching, navigation, and
footer utilities; shortcut help is constrained to the drawer width.

The global language shortcut accepts both `l` and `y`. On the homepage, `n`
and `j` move to the next top-level landing section, `k` moves back, and `h`
toggles focus mode.

## 5. Local search previews

`hugo server` omits the local search index by default. Enable it for an
interactive search check with the documented environment override:

```sh
HUGO_PARAMS_OFFLINESEARCHONSERVE=true hugo server
```

Only the exact environment strings `true` and `false` are normalized; invalid
values still fail the build.

## 6. Verification and release boundaries

From the theme checkout, run:

```sh
node --test 'tests/js/**/*.test.js'
python3 scripts/check-prd7.py
cd exampleSite && hugo --printPathWarnings --panicOnWarning
```

Also inspect representative Docs and Blog roots and leaves in English and
Chinese at desktop, drawer, and narrow-phone widths. A local build or preview
does not establish that a tag, CI release, consumer pin, deployment, or hosted
page is current; record those layers separately.
