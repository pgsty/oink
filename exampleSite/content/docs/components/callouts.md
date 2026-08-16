---
title: Callouts
linkTitle: Callouts
description: GitHub / Obsidian style callouts rendered by the blockquote render hook.
weight: 10
---

## Canonical types

> [!NOTE]
> Five GitHub types render natively on GitHub. This one is a note.

> [!TIP] Tip with a title
> Titles are inline Markdown: `code`, *emphasis*, [links](/docs/).

> [!IMPORTANT]
> Important information.

> [!WARNING]
> Warning: this operation is destructive.

> [!CAUTION]
> Caution: data loss possible.

> [!SUCCESS]
> Everything worked.

> [!DANGER]
> Danger zone.

> [!QUESTION]
> What happens next?

> [!EXAMPLE]
> An example callout with a fenced block:
>
> ```bash
> echo "hello"
> ```

> [!QUOTE]
> Talk is cheap. Show me the code.

## Folded

> [!NOTE]- Collapsed by default
> Click the title to expand. Native `<details>`; works without JavaScript.

> [!TIP]+ Expanded by default
> The `+` sign opens it initially.

> [!DETAILS] Neutral disclosure block
> Collapsed by default because `details` is the neutral folding type.
>
> - lists
> - work here

> [!DETAILS]+ Open details with an icon
> Body.
{icon="fa-solid fa-rocket"}

## Nested content

> [!WARNING] Nested content
> 1. An ordered list
> 2. inside a callout
>
> | A | B |
> | --- | --- |
> | 1 | 2 |
>
> > [!NOTE]
> > Nested callout.

## Unknown type

> [!FOO]- Unknown types stay visible
> Rendered as a plain blockquote with the marker preserved.
