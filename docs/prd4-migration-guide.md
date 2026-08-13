# OINK PRD 4 migration and configuration reference

Version: included in OINK 0.3.0

This reference describes the implementation tracked by
[pgsty/oink#11](https://github.com/pgsty/oink/issues/11). It is not a statement
that the latest OINK tag contains these features. A consuming site may advertise
them only after the owning theme changes are merged, a release tag includes
them, the site pins that tag, and the hosted checks in this document pass.

The normative design decisions remain in the
[machine-checked contract](prd4-navigation-command-palette-contract.md).

## Release status {#release-status}

The implementation in this checkout is assigned to OINK 0.3.0. A consuming
site can adopt the configuration in this guide once the public tag resolves and
the site pins that tag or newer. Do not copy an example into a site still pinned
to an older tag and assume the older theme will understand it.

The release sequence is:

1. merge the owning theme changes;
2. pass the minimum/current Hugo CI matrix;
3. publish a tagged theme release naming PRD 4;
4. update and pin the consumer to that tag;
5. pass consumer CI and hosted smoke tests;
6. only then document the feature as generally available.

## Authority boundaries {#authority-boundaries}

PRD 4 adds behavior, not another information architecture.

| Concern | Authoritative source |
| --- | --- |
| Global navigation | Hugo `menus.main` |
| Sidebar | Hugo content tree and existing docs navigation |
| Product or content-domain switch | Existing root switcher |
| Page discovery | Per-language local search index |
| Page and Palette actions | Shared internal action registry |

Do not add `docs.json`, `navigation.yaml`, or a second menu tree. Quick links
and Palette root order are projections of the same Hugo Menu.

## Migration path {#migration-path}

Flat menus need no migration. To adopt PRD 4 deliberately:

1. keep the site on a branch and pin the containing OINK release when it exists;
2. add one child level to `menus.main` with Hugo `parent` identifiers;
3. select a sidebar icon policy explicitly for new sites;
4. add search metadata to representative pages and cascades;
5. add only safe URL or built-in-ID commands;
6. build both root and subpath variants, then run keyboard and screen-reader
   checks before deployment.

### Upgrade gate {#upgrade-gate}

OINK supports Hugo Extended 0.160.1 and the current CI version. A release must
pass both before a consumer updates. Pin the theme version in `go.mod`; do not
use `@latest` as a production release policy.

### Root and subpath builds {#root-and-subpath-builds}

Use `pageRef` for site-owned menu entries. Hugo then resolves the active
language and `baseURL` correctly:

```sh
hugo --baseURL https://docs.example.com/
hugo --baseURL https://example.com/preview/
```

In the second build, site-owned internal navbar, root-switcher, search-index,
page-action, command, language, and version URLs must remain under `/preview/`.
External destinations—including edit, issue, GitHub, root/version, and
configured-command targets—remain unchanged. Do not hard-code domain-root
paths in a consumer override.

## Nested navigation {#nested-navigation}

One child level is interactive. The parent label remains an ordinary link; its
adjacent button only opens or closes the dropdown or accordion.

```yaml
menus:
  main:
    - identifier: docs
      name: Docs
      pageRef: /docs
      weight: 10
    - identifier: guides
      parent: docs
      name: Guides
      pageRef: /docs/tutorial
      weight: 10
      params:
        icon: fa-solid fa-route
        description: Task-oriented tutorials
    - identifier: reference
      parent: docs
      name: Reference
      pageRef: /docs/reference
      weight: 20
      params:
        icon: fa-solid fa-book
        description: Configuration and API reference
```

An item without children keeps the flat link path. A parent is active when it
or a descendant is current, but only the exact page receives
`aria-current="page"`.

### Navigation interaction {#navigation-interaction}

Parent labels are ordinary links: click navigates to the section landing while
hover or keyboard focus opens the panel. ArrowDown opens and focuses the first
item, Escape closes and restores focus, and a pointer press outside closes it.
Reaching child pages never requires hover.

The navbar has two states — full and compact. The compact state keeps every
item visible as an icon, so there is no separate mobile menu; the former
`navbar_accordion_single_open` accordion parameter is retired and ignored.

Language, version, theme, and search remain in the utility area rather than
becoming children of the content menu.

### Deep menu degradation {#deep-menu-degradation}

Entries below the supported child level emit a Hugo build warning and render
as linked, static group headings with ordinary descendants. They never create
a third-level flyout. Treat the warning as a prompt to move deep information
architecture into the content sidebar, not as permission to suppress it.

### External navigation {#external-navigation}

Cross-host entries receive an external-link affordance and open with
`rel="noopener noreferrer"`. Internal links remain language- and
subpath-aware. The target decision is derived by the theme; site configuration
does not inject arbitrary link behavior.

## Sidebar icon policy {#sidebar-icon-policy}

Set `params.ui.sidebar_icon_policy` to one of:

| Value | Result |
| --- | --- |
| `all` | Every eligible sidebar entry shows its resolved icon. |
| `groups` | Roots and nodes with children show icons; ordinary leaves do not. |
| `none` | Sidebar item icons are omitted. |

The pre-1.0 compatibility default for an absent setting is `all`. New starter
sites explicitly choose `groups`. Invalid values warn and fall back to `all`.
This separates a starter recommendation from a compatibility change.

## Search metadata and index {#search-metadata-and-index}

Local search stays offline-capable and language-separated. PRD 4 extends the
existing index; it does not replace it with a remote service.

### Canonical search fields {#canonical-search-fields}

```yaml
---
title: PostgreSQL configuration
search_keywords: [postgres, postgresql, pg]
search_boost: 1.5
search_exclude: false
---
```

- `search_keywords` accepts one string or an array and participates in Latin
  and CJK substring matching.
- `search_boost` must be a finite positive number and defaults to `1.0`.
  Invalid, zero, negative, infinite, and non-numeric values warn and use
  `1.0`.
- `search_exclude` is the canonical exclusion flag.

`exclude_search` and `excludeSearch` are deprecated for new content but remain
accepted compatibility aliases throughout the 0.x release line. Their earliest
possible removal is the future 1.0 major release, with a changelog entry and
migration notice. Exclusion uses
**any-true-wins** precedence: if any canonical or alias flag is true, the page
is excluded. `search_exclude: false` cannot override a true legacy alias.

### Cascade inheritance {#cascade-inheritance}

Use Hugo cascade for a product or section default, then override individual
pages when needed:

```yaml
---
title: Documentation
cascade:
  search_boost: 1.25
---
```

The index resolves `search_boost` after cascade inheritance. A page-level value
wins through Hugo's normal front matter rules.

### Index schema and fallbacks {#index-schema-and-fallbacks}

Every record keeps `ref`, `title`, `categories`, `tags`, and `excerpt`, and adds
the following deterministic metadata:

| Field | Value and fallback |
| --- | --- |
| `root` | Lower-case `FirstSection`; `home` when no section exists. |
| `section` | Lower-case `CurrentSection`; falls back to `root`. |
| `type` | Lower-case Hugo page type; falls back to `root`. |
| `keywords` | Normalized `search_keywords` array; empty when absent. |
| `boost` | Valid inherited multiplier; otherwise `1.0`. |
| `breadcrumb` | Localized title path from root through the page. |
| `icon` | Page, current section, root, then stable type/root fallback. |

`params.offlineSearchIndex` controls optional text fields:

| Scope | Additional fields |
| --- | --- |
| `title` | No additional text fields. |
| `heading` | `headings` |
| `summary` | `headings`, `description` |
| `content` | `headings`, `description`, `body` |

`summary` is a good starter choice. `content` gives the broadest recall but
usually produces the largest download. Each language emits an independent
index and never falls back to another language's records.

### Ranking behavior {#ranking-behavior}

The final page score is `text match score × search_boost`. Keywords and the
multiplier apply to both Lunr and the deterministic CJK substring path. Stable
title/reference tie-breaks prevent locale- or browser-dependent ordering.
`params.offlineSearchMaxResults` limits page hits; matching Actions are grouped
separately and do not consume the page allowance.

### Index size budget {#index-size-budget}

The regression fixture enforces, per language, at most 2 MiB uncompressed and
512 KiB gzip. A consumer with more content must measure its own generated
indexes and choose `title`, `heading`, `summary`, or `content` deliberately.
The fixture budget is a release guard, not a promise that arbitrary site
content can never exceed it.

## Command Palette and actions {#command-palette-and-actions}

The existing Cmd/Ctrl-K local-search dialog becomes the Command Palette. There
is still one dialog and one local index.

### Palette modes {#palette-modes}

| Input | Results | Index request |
| --- | --- | --- |
| Empty | Quick links, page actions, preferences, configured commands | None |
| Normal text | Pages grouped by root, plus matching Actions | Lazy, same origin |
| Leading `>` | Built-in and configured commands only | None |

`@docs` and `@blog` scopes are not part of the first version. An index failure
does not remove commands, and a stale request cannot overwrite a newer Palette
session.

### Built-in action IDs {#built-in-action-ids}

| ID | Kind | Typical availability |
| --- | --- | --- |
| `copy_markdown` | Invoke | Current page has a Markdown output. |
| `open_chatgpt` | URL | `page_context_menu.assistant_links` is true; uses the current browser URL at activation. |
| `open_claude` | URL | `page_context_menu.assistant_links` is true; uses the current browser URL at activation. |
| `view_markdown` | URL | Current page has a Markdown output. |
| `view_history` | URL | Repository path can be resolved from `github_repo`. |
| `edit_page` | URL | Repository/edit URL can be resolved. |
| `create_issue` | URL | Repository is configured. |
| `print` | Invoke | Interactive HTML output. |
| `switch_theme` | Choice | Theme switching is enabled. |
| `switch_language` | Choice | More than one language target exists. |
| `switch_version` | Choice | Version entries exist. |
| `open_github` | URL | Project repository is configured. |

The corresponding PRD 4 page and Palette actions share descriptors and URL
resolution. Copy text shares one pending/success cache, Print calls the shared
print executor, and theme controls call the same theme application function.
The assistant actions start with real no-JavaScript fallback anchors, then
resolve the deployed host, query string, and fragment from the browser URL at
activation time. Other PRD 4 URL actions keep an href that matches the shared
descriptor. On the page the actions render as a split button beside the
document title — the Copy text primary plus a caret disclosure — replacing the
earlier TOC-rail list. Historical rail-only actions outside the PRD 4 built-in
set remain separate compatibility features, now listed in the same disclosure.

Assistant links are disabled by default because activation sends the full
browser URL to a third party. A site that opts in must avoid secrets in query
strings and fragments, disclose the outbound boundary, and may override the
choice per page with boolean `assistant_links` front matter.

```yaml
params:
  ui:
    page_context_menu:
      assistant_links: true
```

To disable the handoff on a sensitive page while leaving the site-wide opt-in
enabled, set `assistant_links: false` in that page's front matter.

### Custom commands and localization {#custom-commands-and-localization}

Define default-language records under the language's parameters. Translate by
the stable `id`, not array position:

```yaml
languages:
  en:
    params:
      ui:
        command_palette:
          commands:
            - id: status
              title: Service status
              description: View uptime and incidents
              url: https://status.example.com/
              icon: fa-solid fa-signal
              keywords: [uptime, incident]
            - id: print_page
              title: Print this page
              action: print
              keywords: [paper, pdf]
  zh:
    params:
      ui:
        command_palette:
          commands:
            - id: print_page
              title: 打印此页
              keywords: [纸张, PDF]
            - id: status
              title: 服务状态
              keywords: [可用性, 故障]
```

The current language overrides the default record by ID; omitted fields fall
back to the default language. A default record—or a locale-only new ID—must
define exactly one `url` or one allowed built-in `action` ID. An override for
an existing ID may omit both and inherit the default; after merging, every
effective command still has exactly one execution kind.

### Command security boundary {#command-security-boundary}

Configuration is inert data. It cannot provide callbacks, event handlers,
function names, JavaScript source, or an executor. Unknown/reserved IDs,
duplicate IDs, unsupported keys, malformed string fields, `url` plus `action`,
and unknown built-in actions fail the Hugo build.

URLs may be site-relative or explicit `http:`/`https:` URLs. The build rejects
`javascript:`, `data:`, `vbscript:`, `file:`, protocol-relative URLs,
backslashes, and control characters; the runtime validates the URL again.
External URLs use `noopener noreferrer`. Rendering uses escaped template text
or DOM `textContent`; it never evaluates manifest data.

## Keyboard and screen readers {#keyboard-and-screen-readers}

### Navbar interaction table {#navbar-interaction-table}

| Context | Key or action | Result |
| --- | --- | --- |
| Parent link | Enter | Navigate to the parent page. |
| Disclosure button | Enter or Space | Toggle the panel. |
| Desktop disclosure | ArrowDown | Open and focus the first actionable item. |
| Open desktop panel | ArrowUp/Down, Home/End | Move among actionable items. |
| Open desktop panel | Escape | Close and restore disclosure focus. |
| Open desktop panel | Tab or outside press | Leave normally and close the panel. |
| Mobile parent link | Activate | Navigate without toggling the accordion. |
| Mobile disclosure | Activate | Toggle without navigating. |

Disclosure buttons expose `aria-expanded` and `aria-controls`. Panels use the
disclosure pattern, not an ARIA application menu, so child links retain native
link semantics.

### Palette interaction table {#palette-interaction-table}

| Key or action | Result |
| --- | --- |
| Cmd/Ctrl-K | Open or close the Palette. |
| `/` outside an editable control | Open the Palette directly in command mode. |
| ArrowUp/ArrowDown | Move the active listbox option. |
| Cmd/Ctrl-Home or Cmd/Ctrl-End | Move to the first or last option. |
| Enter | Activate the current option once. |
| Escape | Close and restore a visible invoking control. |
| Tab/Shift-Tab | Stay within the modal dialog. |
| IME composition keys | Edit the composition; do not navigate or execute. |

DOM focus stays in the editable combobox while `aria-activedescendant` points
to the active listbox option. Result sections are labelled groups. Disabled
choices with a reason remain discoverable and cannot execute. A polite live
region announces counts, errors, and action outcomes without re-announcing
every arrow movement. Reduced-motion users do not wait for the close
transition. On mobile, focus returns to the visible drawer/menu opener rather
than a control hidden inside the closed surface.

## Runtime and privacy guarantees {#runtime-and-privacy-guarantees}

The Palette capability is enabled only when all conditions hold:

1. `params.offlineSearch` is true;
2. the page is home or uses a shell surface;
3. the current output is not `print`.

When disabled, the page omits Palette dialog markup, its local-index reference,
Lunr, the Palette result model, and the Palette controller. Print output omits
the same runtime. The action manifest and shared page-action registry may still
exist because progressive page actions are independent of search.

Empty and `>` modes do not fetch the index. Normal text fetches only the active
language's same-origin generated JSON. OINK sends no default telemetry, query
upload, analytics event, remote-search request, or assistant URL. A consumer's
explicitly enabled assistant links, analytics, comments, hosted search, or
external command URL are separate site policy and must be disclosed by that
site.

## Compatibility window {#compatibility-window}

- Existing flat `menus.main` HTML and behavior remain supported without
  configuration changes.
- `params.ui.sidebar_icon_policy` remains `all` when absent throughout 0.x;
  starters choose `groups` explicitly.
- `exclude_search` and `excludeSearch` remain search-exclusion aliases
  throughout 0.x and can be removed no earlier than 1.0.
- Cmd/Ctrl-K stays the Palette shortcut and ordinary text remains page search.
- `/` opens command mode only when focus is outside an input, textarea, select,
  or contenteditable region.
- No migration adds a second navigation authority or default network service.

Any alias removal or default change requires a future major-release migration
entry and updated characterization fixtures.

## Starter versus theme defaults {#starter-versus-theme-defaults}

The minimal `exampleSite/hugo.yaml` intentionally demonstrates a nested Hugo
Menu, `sidebar_icon_policy: groups`, summary-sized local search, and safe URL
and built-in commands. These are starter choices. The theme itself continues
to preserve the compatibility defaults for a consumer that configures none of
them.

## Verification and release evidence {#verification-and-release-evidence}

### Local verification gates {#local-verification-gates}

Run the focused theme checks under every supported Hugo version:

```sh
python3 scripts/check-prd4-contract.py
python3 scripts/check-prd4-runtime.py
python3 scripts/check-sidebar-icons.py
python3 scripts/check-prd4-search.py
python3 scripts/check-prd4-actions.py
python3 scripts/check-prd4-palette.py
python3 scripts/check-prd4-docs.py
```

These cover root/subpath output, EN/ZH, flat/nested/deep menus, search on/off,
home/docs/blog/plain/print surfaces, CJK ranking, registry security, Palette
state, and documentation parity. The consumer site must separately run its
Hugo, link, translation, Playwright, and axe suites. Passing one layer is not
evidence that a later delivery layer passed.

### Evidence ledger {#evidence-ledger}

| Gate | Current evidence | Release state |
| --- | --- | --- |
| Contract/runtime/navigation/search/actions/Palette | Focused results in [theme #18](https://github.com/pgsty/oink/issues/18#issuecomment-5263306916) and owning issues; rerun for the release candidate | Prior local pass; current candidate must pass again |
| Consumer root/subpath, EN/ZH, browser and axe | [Consumer #3 evidence](https://github.com/pgsty/oink.pgsty.com/issues/3#issuecomment-5263727126); rerun for the release candidate | Prior local pass; current candidate must pass again |
| Minimum/current Hugo matrix | [Theme CI workflow](../.github/workflows/ci.yml) | Must pass on the merged commit |
| Tagged theme artifact | Release page and checksum for the containing tag | Pending |
| Consumer version pin and deploy | Consumer commit and deployment run | Pending |
| Hosted root/subpath smoke test | Public URLs, observed asset paths, keyboard and telemetry trace | Pending |

Local visual inspection, unit tests, integration tests, CI, package/tag
publication, consumer deployment, and hosted availability are distinct gates.

### Release checklist {#release-checklist}

- [ ] Owning theme changes are reviewed and merged.
- [ ] Hugo 0.160.1 and current-version CI are green on that merge.
- [ ] Changelog and tag name the PRD 4 feature set.
- [ ] Consumer pins the containing tag rather than a local replacement.
- [ ] Consumer non-browser, browser, and axe suites pass in CI.
- [ ] Root and subpath deployments load language-local indexes and internal
      URLs from the correct prefix.
- [ ] Print and search-disabled pages omit Palette runtime.
- [ ] A network trace confirms no default query or telemetry request.
- [ ] Hosted keyboard and screen-reader smoke tests pass.
- [ ] Only after every preceding gate is complete may a consuming site announce
      these features as available to its readers.
