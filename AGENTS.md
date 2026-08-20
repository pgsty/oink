# OINK theme guide

Start with the local maintainer contracts indexed by `docs/README.md`. They are
the active prose source for architecture, component, shell, Landing, and
migration design.

## Repository boundary

- This repository is the OINK Hugo Module: theme implementation, defaults,
  vendored assets, migration tools, focused checkers, and synthetic fixtures.
- Public bilingual documentation, tutorials, examples, case studies,
  integration/browser regression tests, visual review, and deployment belong
  to `../oink.pgsty.com`.
- Do not recreate `exampleSite/` or parallel proposal/design trees. Keep active
  theme contracts compact under `docs/`.
- `tests/site/` is narrow internal input for deterministic theme checkers,
  invalid-input cases, and output goldens. It is not a public example, the
  integration test authority, or the surface used for visual approval.

## Cross-repository workflow

- When public behavior changes, update the implementation, its owning checker,
  and its owning local contract. Update user-facing documentation in
  `../oink.pgsty.com` when the change affects that site.
- Run the smallest owning checker here first. Then validate the real site from
  `../oink.pgsty.com` with the sibling theme replacement:

```sh
HUGO_MODULE_REPLACEMENTS='github.com/pgsty/oink -> /Users/vonng/pgsty/oink' npm test
HUGO_MODULE_REPLACEMENTS='github.com/pgsty/oink -> /Users/vonng/pgsty/oink' npm run test:browser
HUGO_MODULE_REPLACEMENTS='github.com/pgsty/oink -> /Users/vonng/pgsty/oink' hugo server -DFE
```

- Use the documentation site for rendered EN/ZH, desktop/mobile, light/dark,
  accessibility, and interaction review. Never commit a filesystem module
  replacement.
- A local replacement build, a committed change, a public tag, a consumer pin,
  and a deployment are separate completion states.

## Theme contracts

- Hugo Extended 0.160.1 is the compatibility floor.
- Run checkers with `--panicOnWarning` when they build Hugo output. Ordinary
  editing may warn and fall back; publishing gates turn warnings into failures.
- Keep generated `public/`, `resources/`, locks, and caches out of Git.
- Preserve pre-existing changes in this shared worktree and edit only the
  owning implementation, checker, and public Design contract for a change.
