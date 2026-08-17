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
## FileTree — `filetree` fence
```filetree {title="Repository layout"}
- content/                                # site content
- _index.md                             # site home page
- docs/                                 # product guides   {open=false}
- [getting-started.md](/docs/)        # linked entry
- configuration.md
- logs/
- hugo.yaml                               # root:root 0644
- README.md
- LICENSE                                 # {icon="fa-solid fa-scale-balanced" tone=warning}
```
Four-space indent, no title, no comments (single column):
```filetree
src
main.go
internal
server.go
build {type=dir}
```
Pasted `tree` output:
```filetree
.
├── bin
│   └── pig
├── etc
│   └── pig.yml
└── README.md
2 directories, 3 files
```
## Gallery — image list `{.gallery}`
- ![Overview page](shot-a.png)
- ![Detail page](shot-b.png) — Request details
{.gallery}
