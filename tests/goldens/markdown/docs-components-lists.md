# Cards, FileTree, Gallery
> List-based native forms selected by a trailing marker.
---
LLMS index: [llms.txt](/llms.txt)
---
## Cards — link list `{.cards}`
- [Install](/docs/) — Deploy from scratch in five minutes.
- [Configure](/docs/content-primitives/) — Tune the runtime parameters.
- [Operate](/docs/code-blocks/) — Day-two operations and upgrades.
- [Reference](/docs/typography/)
{.cards}
Loose form (description as its own paragraph):
- [Install](/docs/)
Deploy from scratch in five minutes.
- [Configure](/docs/content-primitives/)
Tune the runtime parameters, *with Markdown*.
{.cards}
## FileTree — nested list `{.filetree}`
- content/
- _index.md — site home page
- docs/
- [getting-started.md](/docs/) — linked entry
- configuration.md
- logs/
- hugo.yaml — *root:root 0644*
- `README.md`
{.filetree}
## Gallery — image list `{.gallery}`
- ![Overview page](shot-a.png)
- ![Detail page](shot-b.png) — Request details
{.gallery}
