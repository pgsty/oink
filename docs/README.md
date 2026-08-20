# OINK implementation notes

Status: OINK 0.6.0 draft; compatibility floor: Hugo Extended 0.160.1.

These notes are for theme maintainers. User documentation belongs to
`oink.pgsty.com`; superseded designs belong in Git and `CHANGELOG.md`.

| Document | Authority |
| --- | --- |
| [architecture.md](architecture.md) | Build, configuration, diagnostics, output, security, and performance |
| [components.md](components.md) | Component API, Book/release primitives, and output degradation |
| [shell.md](shell.md) | Navigation, search, blog presentation, actions, and page-end composition |
| [landing-contract.md](landing-contract.md) | Landing data, 22-section registry, runtime, and outputs |
| [migration.md](migration.md) | Supported 0.4 to 0.5 and 0.5 to 0.6 migration boundaries |

Executable behavior remains authoritative: `hugo.yaml` owns published defaults;
owning resolvers and checkers define optional shapes; `layouts/` and `assets/`
own output; check scripts and `tests/goldens/` own validation; `VENDOR.json`
owns bundled versions, licenses, files, and checksums.

Update one owning document with each public contract change. Do not duplicate
implementation detail across notes or add tests that only pin prose.
