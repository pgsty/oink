---
title: Keys
linkTitle: Keys
description: Write shortcuts with `kbd` — one shortcode, a list of key names, a semantic key sequence that stays readable in print and in Markdown output.
weight: 190
search_keywords: [Kbd, shortcut, keyboard, Ctrl, Cmd, chord]
---

Keys separate what the reader has to press from the prose. Use it for shortcuts
and chords: one positional parameter per key, and the theme draws the caps, adds
the separators, and gives screen readers a readable sequence. Command names,
flags and text to type are inline code — they are not physical keys.

## Shortest form {#minimal}

```markdown {title="Source"}
Press {{</* kbd "Ctrl" "K" */>}} to open the command palette.
```

Press {{< kbd "Ctrl" "K" >}} to open the command palette.

Parameters must be quoted, one key per parameter. Fewer than one key, an empty
string, or a named parameter all fail the build.

## A single key {#single}

One parameter is one key, and symbol keys are written as they are.

```markdown {title="Source"}
{{</* kbd "Escape" */>}} closes a dialog;
{{</* kbd "/" */>}} jumps to search;
{{</* kbd "t" */>}} toggles light and dark;
{{</* kbd "l" */>}} cycles through languages.
```

{{< kbd "Escape" >}} closes a dialog;
{{< kbd "/" >}} jumps to search;
{{< kbd "t" >}} toggles light and dark;
{{< kbd "l" >}} cycles through languages.

## Chords {#combo}

Several parameters render in order with `+` between them. That plus sign is
hidden from assistive technology, which hears a localized connector instead.

```markdown {title="Source"}
{{</* kbd "⌘" "Shift" "P" */>}} and {{</* kbd "Ctrl" "Shift" "P" */>}} are the same action.
For a literal plus, treat it as a key of its own: {{</* kbd "Ctrl" "+" */>}} zooms the page in.
```

{{< kbd "⌘" "Shift" "P" >}} and {{< kbd "Ctrl" "Shift" "P" >}} are the same action.
For a literal plus, treat it as a key of its own: {{< kbd "Ctrl" "+" >}} zooms the page in.

## Platform differences {#platforms}

Write the label printed on the reader's keyboard: `⌘` on macOS, `Ctrl` on
Windows and Linux. Never merge two platforms into one sequence — a spelling like
`Ctrl/⌘` cannot be read aloud correctly. Say which platform in the sentence, or
split into [tabs](/docs/tabs/).

```markdown {title="Source"}
On macOS press {{</* kbd "⌘" "K" */>}}; on Windows and Linux, {{</* kbd "Ctrl" "K" */>}}.
```

On macOS press {{< kbd "⌘" "K" >}}; on Windows and Linux, {{< kbd "Ctrl" "K" >}}.

## Shortcut tables {#in-tables}

A cheatsheet is where keys most often live. Here are some of the global keys
this site honours:

```markdown {title="Source"}
| Key | Action |
| --- | --- |
| {{</* kbd "Ctrl" "K" */>}} | Open the command palette ({{</* kbd "⌘" "K" */>}} on macOS) |
| {{</* kbd "/" */>}} | The palette's full search state |
| {{</* kbd "t" */>}} | Toggle light and dark |
| {{</* kbd "q" */>}} / {{</* kbd "e" */>}} | Previous / next page |
| {{</* kbd "w" */>}} {{</* kbd "s" */>}} {{</* kbd "a" */>}} {{</* kbd "d" */>}} | Move, collapse and expand in the sidebar tree |
| {{</* kbd "Escape" */>}} | Leave the sidebar tree for the article |
```

| Key | Action |
| --- | --- |
| {{< kbd "Ctrl" "K" >}} | Open the command palette ({{< kbd "⌘" "K" >}} on macOS) |
| {{< kbd "/" >}} | The palette's full search state |
| {{< kbd "t" >}} | Toggle light and dark |
| {{< kbd "q" >}} / {{< kbd "e" >}} | Previous / next page |
| {{< kbd "w" >}} {{< kbd "s" >}} {{< kbd "a" >}} {{< kbd "d" >}} | Move, collapse and expand in the sidebar tree |
| {{< kbd "Escape" >}} | Leave the sidebar tree for the article |

The complete list of site-wide shortcuts is in
[keyboard navigation](https://oink.pgsty.com/docs/customize/keyboard/).

## In steps {#in-steps}

```markdown {title="Source"}
1. Press {{</* kbd "Ctrl" "K" */>}} to open the command palette
1. Type `>` for the command-only state, or type a keyword to search
1. Select with {{</* kbd "↑" */>}} {{</* kbd "↓" */>}} and press {{</* kbd "Enter" */>}} to go
1. {{</* kbd "Escape" */>}} closes it and focus returns where it was
{.steps}
```

1. Press {{< kbd "Ctrl" "K" >}} to open the command palette
1. Type `>` for the command-only state, or type a keyword to search
1. Select with {{< kbd "↑" >}} {{< kbd "↓" >}} and press {{< kbd "Enter" >}} to go
1. {{< kbd "Escape" >}} closes it and focus returns where it was
{.steps}

## Raw `<kbd>` tags {#raw-kbd}

A raw `<kbd>` tag in Markdown gets the same styling, and GitHub renders it too.
The difference is that the separators and the accessible sequence are then yours
to maintain: either spelling works for a single key, but use the shortcode for
chords.

```markdown {title="Source"}
Press <kbd>F5</kbd> to reload; in an editor, <kbd>Ctrl</kbd>+<kbd>S</kbd> saves.
```

Press <kbd>F5</kbd> to reload; in an editor, <kbd>Ctrl</kbd>+<kbd>S</kbd> saves.

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | `<span class="td-kbd-sequence">` around one `<kbd>` per key; the visible `+` is hidden from screen readers, which get a localized connector |
| Print | Same as HTML, static |
| Markdown | Plain text: `Ctrl + K`, `⌘ + Shift + P` |
| RSS | Same as print |

Without CSS or JavaScript the instruction is still readable.

## Parameter reference {#reference}

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| Positional 1..n | string | — | At least one; each must be non-empty and quoted; order is display order |
{.fields meta="type default"}

Positional parameters only. There is no `separator`, `label`, `platform`,
`class` or `size`: Hugo does not allow positional and named parameters in one
shortcode call.

## Limits {#limits}

- One sequence is one set of keys pressed together: press-A-then-B is two `kbd`
  calls and a sentence — press {{< kbd "Escape" >}}, then {{< kbd "Enter" >}}.
- No platform detection: the page never swaps `Ctrl` for `⌘` based on the
  visitor's operating system.
- No key mapping or recording: menu paths, gestures and gamepads are out of
  scope.
- Missing quotes fail the build: `Ctrl` in `{{</* kbd Ctrl K */>}}` is not a
  string parameter.
- Do not use it for commands: `hugo server` is inline code; `Ctrl` is a key.

## Related {#related}

- [Keyboard navigation](https://oink.pgsty.com/docs/customize/keyboard/) — the full shortcut list and its switches
- [Command palette](https://oink.pgsty.com/docs/customize/panel/) — what {{< kbd "Ctrl" "K" >}} opens
- [Badges](/docs/badge/) — the other inline shortcode
- [Steps](/docs/steps/) — the container for instructions
