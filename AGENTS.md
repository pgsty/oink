# OINK theme guide

`CLAUDE.md` is a symbolic link to this file. Edit `AGENTS.md` only.

Start with the canonical bilingual Design section in the sibling documentation
site at `../oink.pgsty.com/content/docs/design/`. It owns maintainer contracts,
accepted decisions, dated research, and active proposals.

## Current baseline

The current release is `v1.5.1`, dated 2026-11-06 in `CHANGELOG.md`. The sibling
site's `v1.5.1` Design contracts describe this release. Work merged after the
latest tag accumulates under `## Unreleased` in `CHANGELOG.md` until the next
release. Refresh Git state, public tags, and consumer pins before making claims
about later releases or downstream adoption.

## Repository boundary

- This repository is the OINK Hugo Module: theme implementation, defaults,
  vendored assets, migration tools, focused checkers, and synthetic fixtures.
  The root is the module; there is no site, npm workspace, or generated build
  input. Hugo Extended is the build tool.
- Public bilingual documentation, tutorials, examples, case studies,
  integration/browser regression tests, visual review, and deployment belong
  to `../oink.pgsty.com`.
- The optional Go executable `oink`, including native site checks, guarded
  maintenance plans, and workspaces, belongs to `../oink-cli`. It has its own
  version and release lifecycle; ordinary Hugo consumers do not require it.
- `hugo.yaml`, owning resolvers/checkers, and `VENDOR.json` own executable
  configuration and dependency facts. Generated schemas must follow those
  sources; do not introduce a second configuration authority in the CLI.
- Do not recreate `exampleSite/`, `docs/`, `plan/`, `plans/`, `proposal/`, or
  another repository-local design tree.
- `tests/site/` is narrow internal input for deterministic theme checkers,
  invalid-input cases, and output goldens. It is not a public example, the
  integration test authority, or the surface used for visual approval.

## Cross-repository workflow

- When public behavior changes, update the implementation, its owning checker,
  and both language versions of the affected contract under
  `../oink.pgsty.com/content/docs/design/` in the same delivery.
- Put every new PRD, RFC, or design proposal in
  `../oink.pgsty.com/content/docs/design/proposals/<slug>.md` with a matching
  `<slug>.zh.md`. Follow that section's published lifecycle and template;
  publication is not proof of implementation, and a proposal stays
  non-normative until it is implemented and accepted.
- Put accepted rationale under `content/docs/design/decisions/` in the site
  repository and dated, non-normative evidence under `research/`. Preserve
  retired drafts in Git history and `CHANGELOG.md`, not a local planning tree.
- Run the smallest owning checker here first. Then validate the real site
  through its sibling-checkout Make targets:

```sh
make -C ../oink.pgsty.com check
make -C ../oink.pgsty.com browser
make -C ../oink.pgsty.com dev
```

- Owning output checkers normally build fresh fixtures. Use `--public` only
  when deliberately reusing output whose theme/configuration is identified.
  `bin/test_site.py` owns the 120-second limit for its Hugo subprocesses.
- Use the documentation site for rendered EN/ZH, desktop/mobile, light/dark,
  accessibility, and interaction review. Never commit a filesystem module
  replacement.
- The site's `check`, `browser`, and `dev` targets use this local theme through
  an inline `HUGO_MODULE_REPLACEMENTS`; `build` and `serve` use its published
  pin by default. Published-pin checks must disable inherited replacements and
  both workspaces. Local regression success does not establish that the public
  module or hosted site contains these changes.
- A local replacement build, a committed change, a public tag, a consumer pin,
  and a deployment are separate completion states.

## Focused theme checks

Run the checker that owns a change. `.github/workflows/ci.yml` is the complete
ordered theme-unit suite and pins the toolchain.

```sh
python3 bin/check-shell.py                    # shell, blog, page-end contracts
python3 bin/check-components.py               # component and render-hook contracts
python3 bin/check-output.py                   # fresh fixture + output structure/security
python3 bin/check-namespace.py                # fresh fixture + naming namespace
python3 bin/check-goldens.py                  # HTML/print/Markdown/RSS/LLMS goldens
python3 bin/check-params.py                   # config shapes and warning fallbacks
python3 bin/check-i18n.py                     # locale schema parity
python3 bin/generate-config-schema.py --check # generated schemas match their sources
node --test 'tests/js/**/*.test.js'           # browser-runtime units
hugo --source tests/site --printPathWarnings  # regression fixture with diagnostics
```

- Output checkers build into a temporary directory when invoked as shown and
  accept `--hugo`. Pass `--public` only to reuse a fixture that was built
  separately and is known to be fresh; that mode does not rebuild it.
- `check-goldens.py --update` records an intentional behavior change; it is
  never cleanup.
- The theme Makefile's `c` and `clean` targets delete generated files; they are
  not check targets.

Migration is dry-run unless `--write` is explicit. The toolkit rewrites only
content Markdown and supported YAML front matter; it does not edit site
configuration, data, layouts, assets, or modules.

```sh
python3 bin/migrations/oink06.py report --sites <dir>...
python3 bin/migrations/oink06.py migrate --site <dir> [--write]
python3 bin/migrations/oink06.py check --site <dir>
python3 -m unittest discover -s tests/migrations -t .
```

## Releases

- `main` is the sole long-lived branch and carries the next release. Immutable
  `vX.Y.Z` tags are the stable-release authority and count as published only
  after push and Go-proxy verification. Never move a tag; a published mistake
  receives a new patch release. Do not keep a `release` branch that merely
  duplicates a tag.
- Report release state precisely: source complete → locally validated →
  committed → tagged → pushed/proxy verified → consumer pinned → deployed →
  production-identical. A green local build proves only local validation.

## After a theme release

- Include downstream adoption when releasing a new OINK version. Inventory
  the primary Hugo checkouts under `~/www` and `~/pgsty` with
  `python3 bin/update-consumers.py <tag>`, then update and validate them with
  `--write --check`. Read each site's instructions and preserve unrelated work.
- The inventory skips linked worktrees, non-default branches, hidden copies,
  and nested archives. Review every blocked or skipped result; use `--sites`
  for an explicitly selected checkout. Review vendored changes before using
  `--refresh-vendor`; a go.mod bump alone does not upgrade vendored output.
- Inventory also includes primary `site/` directories and reports classic
  `themes/oink` consumers. Update their clean submodule or reviewed source copy
  separately, preserve offline builds, and run the site's owning checks.
- Check exact published module resolution with local replacements and both
  workspace mechanisms disabled. Update current version references in site
  READMEs/configuration, and run each site's relevant checks. Keep historical
  release notes unchanged. Commit, push, and deployment remain separate steps.
- Maintained consumers use `params.ui.preset: paper` and the explicit
  `preset_menu: [paper, slate, ink, terminal]` list. Preserve this reader-choice
  policy on later upgrades, and check rendered menus as well as configuration.
  Use `--check --check-appearance` to verify the published pin and entry menus.
  Review custom shells separately. Select reviewed source-only sites with
  `--sites`; leave superseded migration copies out of the maintained set.

## Theme contracts

### Toolchain and diagnostics

- Use OINK v1.5.1 and Hugo Extended 0.168.0 for maintained consumer sites,
  development, CI, and release checks. Keep this baseline pinned; `theme.toml`
  declares it as `min_version`. Update requirements, checkers, and current
  bilingual contracts together. Keep the upstream LibSass deprecation warning
  visible and accepted.
- SCSS uses Hugo Extended's built-in LibSass, including main and ReDoc styles.
  Ordinary consumers must not install Dart Sass or another Sass executable.
  Preserve project-variable/style hooks. Future Hugo upgrades must preserve
  this dependency boundary; do not add compatibility shims for unrelated versions.
- The module declares Go 1.27.3 as its minimum; the current development default
  is Go 1.27.3. Record the actual local tool versions when reporting validation.
- Do not enable `--panicOnWarning` or `HUGO_PANICONWARNING` in any build,
  checker, preview, or CI job. Review diagnostics and verify their owning
  output contracts. Invalid-input tests check warnings and safe fallback
  output directly; warnings do not change Hugo's exit status.
- Keep generated `public/`, `resources/`, locks, and caches out of Git.
- Preserve pre-existing changes in this shared worktree and edit only the
  owning implementation, checker, and public Design contract for a change.

### Implementation contracts

- Reading shells are `docs`, `book`, `blog`, and `swagger`; `type: expo` reuses
  the shell. `params.ui.shell_types` (default `[docs, book, blog, swagger, expo]`)
  lists the content types that receive it. Landing is a layout. Immersive
  reading is the ordinary blog shell with hero/TOC-flow/clouds/sidebar keys,
  never an `article` type or second shell. The blog shell defaults its
  breadcrumb off; `breadcrumb` stays an ordinary key.
- Render content once through `content/render.html` before `scripts.html`.
  Shortcodes and hooks set Page Store capability flags; script selection reads
  them afterwards. Give each new runtime a stable `js/chunks/` target, and put
  language/config identity in that target whenever its generated bytes vary.
- HTML is semantic-first and progressively enhanced. Print is static and
  expanded; Markdown/LLMS contains no component markup; RSS is safe static
  output or explicit omission. Consumers opt into expensive custom outputs.
- Invalid author/config input warns, uses a documented safe fallback or emits
  nothing, and keeps ordinary `hugo server` usable. Never call `errorf` or add
  speculative validation for unreachable internal states.
- Theme policy lives under `params.ui.*`; page overrides drop `ui.`. Boolean
  switches are bare booleans unless a multi-setting feature also accepts a
  boolean shorthand. Public renames get a targeted owning-resolver warning, a
  migration note, and a negative test—not a global compatibility registry.
- Theme-owned network features are off until explicitly and completely
  configured. A normal build downloads nothing. Vendored artifact, license,
  version, and checksum change together in `VENDOR.json`. Do not prune vendored
  fonts or Font Awesome by apparent template usage; the complete supported
  distribution is public authoring surface.
- Shortcode and component labels are plain text; Landing narrative fields may
  render Markdown. Icons are one Font Awesome class pair. Shared attribute and
  URL policies drop unsafe output rather than repairing it in the browser.
- CSS uses `td-` classes, `data-td-*`, `--td-*`, logical properties, and covers
  RTL, print, forced colors, reduced motion, narrow screens, and long tokens.
  Author markers such as `.steps` and `.cards` remain unprefixed.
- Keep all 32 locale files schema-identical and natively translated. Add every
  user-visible string to every locale, preserve its runtime placeholders, and
  run `bin/check-i18n.py`; the checker never manufactures English fallbacks.
- Override the narrowest partial. Do not merge base templates when that changes
  Hugo lookup precedence or copy a full shell for one feature.
- The public surface is 29 shortcodes, 22 Landing sections, shared output and
  security rules, and the blog hero/index/authors/series/share contracts. Their
  bilingual maintainer references are published under
  `../oink.pgsty.com/content/docs/design/`.

## Git 内容与大文件规则

用户于 2026-10-10 明确的通用仓库规则：

- 仓库默认保存源代码、配置和必要的轻量文档、元数据。构建产物、可执行文件、软件包、容器/虚拟机镜像、下载压缩包、数据库导出和大体积原始数据默认不进入 Git；文本格式的数据大文件同样需要检查。
- 在工作树内下载或生成上述文件之前，先选择仓库外的制品/数据位置，或补上合理的 `.gitignore` 规则并验证实际路径已被忽略，防止暂存和代理恢复/差异快照将它们写入 Git 对象库。
- 暂存、提交前检查新增文件的大小、类型和 staged 文件列表，只加入本次需要的源文件；不得用强制添加绕过忽略规则。优先保留来源清单、校验值及可复现的下载/构建方法。
- 对二进制素材、数据集或生成文件是否应纳入版本控制拿不准时，先问用户，再暂存或提交；确需例外时也先取得用户明确指示。
- 本规则不授权删除已有文件、stash、恢复快照或改写 Git 历史。忽略规则不会清除已存在的 Git 对象，历史清理需要单独明确范围。
