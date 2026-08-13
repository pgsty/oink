# PRD 4 navigation and Command Palette contract

Version: included in OINK 0.3.0

Contract version: 1

Tracking issue: [pgsty/oink#11](https://github.com/pgsty/oink/issues/11)

This document freezes the public decisions that later PRD 4 changes must
preserve. The machine-readable companion is
tests/fixtures/prd4/contract.json; CI checks that the two stay aligned. The
release-facing migration reference is available in
[English](prd4-migration-guide.md) and
[Simplified Chinese](prd4-migration-guide.zh.md).

The contract deliberately separates public decisions from rendered
observations. scripts/check-prd4-contract.py records the implementation across
the complete fixture matrix. A change to an observation must update the
relevant assertion and explain whether it is a compatible change.

## Authority boundaries

PRD 4 does not add another information architecture:

- Hugo Menu is the global-navigation authority.
- The Hugo content tree and current docs navigation are the sidebar authority.
- The existing root switcher owns product or documentation-domain switching.
- The per-language local search index is the shared discovery and command
  source.

docs.json, navigation.yaml, or another parallel navigation tree is outside
this contract.

## Navigation contract

Only one child level is interactive. A parent with children renders a
navigable label and a separate disclosure button on desktop and mobile. No
operation depends on hover.

Parent labels are ordinary links: click navigates to the section landing, while
hover or keyboard focus opens the panel. ArrowDown opens the dropdown and
focuses its first actionable item, Escape closes it and restores focus, and an
outside press closes it. The parent link owns aria-expanded and aria-controls.

The navbar has exactly two states, full and compact; the compact state keeps
every item visible as an icon, so there is no separate mobile menu and the
former params.ui.navbar_accordion_single_open accordion parameter is retired.
On shell pages below md an extra icon opens the sidebar drawer.

The parent is active when it or any descendant is current. External links have
an explicit visual affordance and include noopener noreferrer when opened in a
new browsing context.

Deeper menu input emits a build warning and degrades to content under a group
heading. It never creates a third-level flyout.

## Sidebar icon contract

params.ui.sidebar_icon_policy accepts:

- all: every eligible item shows its resolved icon;
- groups: roots and nodes with children show icons, ordinary leaves do not;
- none: sidebar item icons are omitted.

An absent setting remains all before 1.0. Version 1.0 is the earliest release
that may reconsider this default; it does not imply that 1.0 will change it.
New starter sites explicitly choose groups. Invalid input warns and falls back
to the compatibility default.

## Search schema and ranking contract

Canonical front matter:

- search_keywords: additional query terms;
- search_boost: a finite positive multiplier, default 1.0;
- search_exclude: the canonical exclusion flag.

exclude_search and excludeSearch are deprecated for new content and cannot be
removed before 1.0. Version 1.0 is the earliest release that may remove them,
with a major-release migration notice. If any canonical or compatibility
exclusion flag is true, the page is excluded. A false canonical value does not
override a true legacy alias.

Every indexed document keeps the existing fields and adds root, section, type,
keywords, boost, breadcrumb, and icon. Missing metadata uses deterministic
fallbacks derived from Hugo's page and section tree:

- root is the lower-case first-section key;
- section is the lower-case current-section key, falling back to root;
- type is the lower-case Hugo page type, falling back to root;
- breadcrumb is the localized LinkTitle/Title path from root through the page;
- icon resolves from page, current section, root, then a stable type/root icon;
- search_keywords accepts a scalar or array and is always emitted as an array;
- search_boost resolves after Hugo cascade inheritance; a non-numeric,
  non-finite, zero, or negative value warns and emits the default 1.0.

The final score is text match score multiplied by search_boost. The multiplier
and keywords apply to Lunr and the CJK substring fallback. Indexes remain
separated by language and all references remain correct under subpath
deployment. Each language index has a 2 MiB uncompressed and 512 KiB gzip
budget. The search-metadata implementation issue may tighten these ceilings,
but cannot remove the measured budget gate.

## Command registry contract

The built-in action IDs are copy_markdown, open_chatgpt, open_claude,
view_markdown, view_history, edit_page, create_issue, print, switch_theme,
switch_language, switch_version, and open_github.

Corresponding PRD 4 page and Palette actions share internal descriptors and URL
resolution. Copy text and Print also share their registry executors; assistant
actions resolve the browser URL at activation time, and theme controls call the
same theme application function. On the page surface the actions render as a
split button beside the document title: Copy text is the primary half and the
caret disclosure lists the full set. Historical rail-only compatibility actions
outside the PRD 4 built-in set remain out of scope.
Availability, title, description, icon, keywords, execution kind, URL, and
disabled reason are data rather than duplicated behavior.

Configured commands may reference a built-in action ID or a URL. Configuration
cannot inject a JavaScript callback. Localized command titles and keywords live
under languages.<lang>.params.ui.command_palette.commands, with the site's
normal language fallback.

## Palette modes

The current local-search dialog becomes the Command Palette; PRD 4 does not add
a second modal.

- Empty query: quick links, context-aware page actions, theme, language,
  version, and configured commands.
- Text query: page fields, page keywords, and commands, grouped by content root
  and Actions.
- A greater-than prefix: commands only.

The first version does not add @docs or @blog scopes.

Cmd/Ctrl-K, `/` outside editable controls, keyboard result navigation, Escape,
focus restoration, live-region announcements, reduced motion, and mobile
interaction remain part of the existing dialog's accessibility contract. The
slash shortcut opens directly in command-only mode and yields to inputs,
textareas, selects, and contenteditable regions.

## Runtime contract

The local Palette capability is true only when all of these conditions hold:

1. params.offlineSearch is enabled;
2. the page is home or uses a shell surface;
3. the current output is not print.

When the capability is false, the build omits the dialog, local index, Lunr,
and Palette controller. Print follows the same omission rule.

No default telemetry request or assistant URL handoff is allowed. Built-in
assistant links are an explicit site opt-in because activation sends the full
browser URL, including query and fragment, to the selected third party.

The runtime-isolation implementation in
[pgsty/oink#13](https://github.com/pgsty/oink/issues/13) makes the capability
predicate authoritative for dialog markup, the local index reference, Lunr,
and the Palette controller.

## Compatibility and non-goals

Existing flat Hugo menus remain valid without configuration changes. PRD 4
does not include AI-powered or semantic search, a remote search replacement,
personalized recommendations, arbitrary-depth flyouts, a second navigation
authority, or default query upload. Optional assistant handoff links are page
actions, not search or autonomous AI behavior.

## Characterization matrix

scripts/check-prd4-contract.py builds temporary bilingual sites with local
search off and on. It covers both root deployment and a /preview/ subpath. It
normalizes the desktop and mobile menu into link records and records runtime
markers for these surfaces:

| Surface | Representative output |
| --- | --- |
| Home | /preview/en/ and /preview/zh/ |
| Docs shell | localized tutorial page |
| Blog shell | localized blog root |
| Plain project | localized non-shell page |
| Print | localized docs print output |

The flat menu snapshot is a compatibility guard. Nested fixtures verify the
split parent link/disclosure behavior on desktop and mobile. The deep fixture
verifies the warning and static-group degradation contract without creating a
third-level flyout.
