# OINK theme guide

Start with the canonical bilingual Design section in the sibling documentation
site at `../oink.pgsty.com/content/docs/design/`. It owns maintainer contracts,
accepted decisions, dated research, and active proposals.

## Repository boundary

- This repository is the OINK Hugo Module: theme implementation, defaults,
  vendored assets, migration tools, focused checkers, and synthetic fixtures.
- Public bilingual documentation, tutorials, examples, case studies,
  integration/browser regression tests, visual review, and deployment belong
  to `../oink.pgsty.com`.
- Do not recreate `exampleSite/`, `docs/`, `plan/`, `plans/`, `proposal/`, or
  another repository-local design tree.
- `tests/site/` is narrow internal input for deterministic theme checkers,
  invalid-input cases, and output goldens. It is not a public example, the
  integration test authority, or the surface used for visual approval.

## Cross-repository workflow

- When public behavior changes, update the implementation, its owning checker,
  and both language versions of the affected contract under
  `../oink.pgsty.com/content/docs/design/`.
- Put every new PRD, RFC, or design proposal in
  `../oink.pgsty.com/content/docs/design/proposals/<slug>.md` with a matching
  `<slug>.zh.md`. Follow that section's published lifecycle and template;
  publication is not proof of implementation.
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

- Use the documentation site for rendered EN/ZH, desktop/mobile, light/dark,
  accessibility, and interaction review. Never commit a filesystem module
  replacement.
- A local replacement build, a committed change, a public tag, a consumer pin,
  and a deployment are separate completion states.

## Theme contracts

- Hugo Extended 0.160.1 is the compatibility floor. On 0.160.x, configure a
  non-default generic `zh` language alongside the regional Chinese catalogs
  with `locale: zh-CN`; bare `locale: zh` works there from 0.161 onward.
- Run checkers with `--panicOnWarning` when they build Hugo output. Ordinary
  editing may warn and fall back; publishing gates turn warnings into failures.
- Keep generated `public/`, `resources/`, locks, and caches out of Git.
- Preserve pre-existing changes in this shared worktree and edit only the
  owning implementation, checker, and public Design contract for a change.
