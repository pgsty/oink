---
title: Cards, FileTree, Gallery
linkTitle: Cards / FileTree / Gallery
description: List-based native forms selected by a trailing marker.
outputs: [HTML, markdown]
weight: 30
---

## Cards — link list `{.cards}`

- [Install](/docs/) — Deploy from scratch in five minutes.
- [Configure](/fixtures/content-primitives/) — Tune the runtime parameters.
- [Operate](/fixtures/code-blocks/) — Day-two operations and upgrades.
- [Reference](/fixtures/typography/)
{.cards}

Loose form (description as its own paragraph):

- [Install](/docs/)

  Deploy from scratch in five minutes.

- [Configure](/fixtures/content-primitives/)

  Tune the runtime parameters, *with Markdown*.
{.cards}

## Task lists

- [x] Render the static status
- [ ] Label the disabled checkbox at runtime

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

## Gallery — the `gallery` fence

```gallery
![Overview page](shot-a.png)
![Detail page](shot-b.png) # Request details
```
