# OINK implementation notes

This directory records the current OINK 0.5 implementation contract. It is for
theme maintainers; user documentation belongs to `oink.pgsty.com`.

Only current behavior lives here. Superseded proposals and release history stay
in Git and `CHANGELOG.md`, not beside the active contract.

| Document | Authority |
| --- | --- |
| [architecture.md](architecture.md) | Build, configuration, output, security, runtime, typography, and performance boundaries |
| [components.md](components.md) | Component API, Book/release primitives, and output degradation |
| [shell.md](shell.md) | Navigation, search, actions, keyboard behavior, and page-end composition |
| [landing-contract.md](landing-contract.md) | Landing data sources, section registry, and output behavior |
| [migration.md](migration.md) | Supported 0.4 to 0.5 source and configuration migration |

The implementation remains the executable authority:

- `hugo.yaml` owns defaults and parameter shapes.
- `layouts/` and `assets/` own rendered behavior.
- `tests/fixtures/navigation/contract.json` owns the navigation test matrix.
- `tests/goldens/` owns representative HTML, print, Markdown, RSS, and LLMS
  output.
- `VENDOR.json` owns third-party versions, files, licenses, and checksums.

Update the relevant note in the same change as a public behavior change. Do not
copy implementation details into several documents or add text-presence tests:
behavioral checks should exercise templates and rendered output.
