---
title: Steps
linkTitle: Steps
description: An ordered list plus `{.steps}` becomes a numbered procedure with dots and a connecting rule; switch to the steps shortcode when each step needs a heading in the table of contents.
weight: 70
search_keywords: [Steps, ordered list, procedure, tutorial, ol, start, TOC]
---

Steps are an ordered list with numbered dots and a rule running through them: a
plain ordered list plus a `{.steps}` marker line. The dots and the rule are
drawn in CSS and no script is loaded. Use it for procedures that have an order.
Parallel items with no order belong in a plain list or in cards.

There are two spellings: an ordered list plus `{.steps}` (the default choice),
and the `{{%/* steps */%}}` shortcode, for when each step needs its own heading
and those headings belong in the table of contents.

## Shortest form {#minimal}

Write `1.` for every item and let Markdown do the counting. Inserting, deleting
and reordering steps then needs no renumbering, and the content indent is always
three spaces.

```markdown {title="Source"}
1. Install Hugo Extended
1. Clone the documentation site
1. Start the local preview
{.steps}
```

1. Install Hugo Extended
1. Clone the documentation site
1. Start the local preview
{.steps}

`{.steps}` must touch the last line of the list; leave a blank line and it turns
into a visible line of braces.

## What goes in a step {#blocks}

A list item takes any block content: paragraphs, fenced code, callouts, tables,
nested lists, images. Indent it to the item's content column — three spaces.

````markdown {title="Source"}
1. Clone the documentation site; it is itself a complete example of the theme.

   ```bash
   git clone https://github.com/pgsty/oink.pgsty.com my-docs
   cd my-docs
   ```

1. Start the local server.

   ```bash
   hugo server
   ```

   > [!NOTE]
   > The first build fetches the theme through the Go module proxy, which needs
   > Go on the machine.

1. Replace three things and it is your site.

   | Where | Replace with |
   | --- | --- |
   | `title` in `hugo.yaml` | your site name |
   | `baseURL` in `hugo.yaml` | your domain |
   | `content/` | your content |
{.steps}
````

1. Clone the documentation site; it is itself a complete example of the theme.

   ```bash
   git clone https://github.com/pgsty/oink.pgsty.com my-docs
   cd my-docs
   ```

1. Start the local server.

   ```bash
   hugo server
   ```

   > [!NOTE]
   > The first build fetches the theme through the Go module proxy, which needs
   > Go on the machine.

1. Replace three things and it is your site.

   | Where | Replace with |
   | --- | --- |
   | `title` in `hugo.yaml` | your site name |
   | `baseURL` in `hugo.yaml` | your domain |
   | `content/` | your content |
{.steps}

Shortcodes in `{{</* … */>}}` form — tabs, cards, badges — work inside a list
item too. The `{{%/* … */%}}` form does not; see [Limits](#limits).

## Splitting one step per platform {#tabs-in-steps}

When one step differs per platform, write the `{tab=}` fences side by side
inside that list item and they still assemble into a tab set.

`````markdown {title="Source"}
1. Install Hugo Extended.

1. Install the dependencies:

   ```bash {tab="EL / RHEL" group="stepdemo" value="rpm"}
   sudo dnf install golang git
   ```
   ```bash {tab="Debian / Ubuntu" value="deb"}
   sudo apt install golang-go git
   ```

1. Run `hugo server` to preview.
{.steps}
`````

1. Install Hugo Extended.

1. Install the dependencies:

   ```bash {tab="EL / RHEL" group="stepdemo" value="rpm"}
   sudo dnf install golang git
   ```
   ```bash {tab="Debian / Ubuntu" value="deb"}
   sudo apt install golang-go git
   ```

1. Run `hugo server` to preview.
{.steps}

## Continuing the numbering {#start}

When prose interrupts a procedure, write the first item of the next group with
its real number. Markdown emits `start` and the numbering continues from there
(up to 40).

```markdown {title="Source"}
4. Configure `baseURL` and the deployment workflow.
1. Push to `main` and wait for GitHub Actions to finish.
{.steps}
```

4. Configure `baseURL` and the deployment workflow.
1. Push to `main` and wait for GitHub Actions to finish.
{.steps}

## Steps with headings {#shortcode}

When the procedure is long and each step deserves a heading that can be linked
to and collected by the table of contents, use `{{%/* steps */%}}`: its body is
page-level Markdown, every direct child heading is one step, and the body is not
indented. The three headings below appear in this page's table of contents.

```markdown {title="Source"}
{{%/* steps */%}}

### Install the toolchain {#install-toolchain}

You need Hugo Extended ≥ 0.160.1 and Go.

### Run the server {#run-server}

{{</* tabs group="oink-os" default="macos" */>}}
{{</* tab label="macOS" value="macos" */>}}
`brew install hugo go`
{{</* /tab */>}}
{{</* tab label="Debian" value="debian" */>}}
`sudo apt install hugo golang-go`
{{</* /tab */>}}
{{</* /tabs */>}}

### Publish {#publish}

Push to `main`; the workflow the repository ships builds and publishes.

{{%/* /steps */%}}
```

{{% steps %}}

### Install the toolchain {#install-toolchain}

You need Hugo Extended ≥ 0.160.1 and Go.

### Run the server {#run-server}

{{< tabs group="oink-os" default="macos" >}}
{{< tab label="macOS" value="macos" >}}
`brew install hugo go`
{{< /tab >}}
{{< tab label="Debian" value="debian" >}}
`sudo apt install hugo golang-go`
{{< /tab >}}
{{< /tabs >}}

### Publish {#publish}

Push to `main`; the workflow the repository ships builds and publishes.

{{% /steps %}}

This is the theme's only `{{%/* … */%}}` shortcode. The percent form hands its
body to Goldmark as page-level Markdown, which is the only way its headings can
reach the table of contents and the only way container shortcodes such as
`tabs`, `cards` and `fields` can live inside it. The price is that it cannot
nest inside a list item or inside another percent container.

Keep the headings of one procedure at one level, and never nest one `steps`
inside another.

## Which form to use {#which}

| Situation | Use |
| --- | --- |
| A step is a sentence or two plus a command | ordered list + `{.steps}` |
| Each step needs a heading, a link and a place in the TOC | `{{%/* steps */%}}` |
| A step must contain a `tabs`, `cards` or `fields` container | `{{%/* steps */%}}` |
| The procedure itself has to nest inside another list item | ordered list + `{.steps}` |

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | The native form is `<ol class="steps">` with numbers and rule drawn in CSS; the shortcode form is `<div class="td-steps">` plus headings |
| Print | Numbers and content unchanged, the rule stays |
| Markdown | The source as written: an ordered list plus `{.steps}`, or headings plus bodies |
| RSS | A static list or titled sections |

No script; with JavaScript off nothing changes.

## Parameter reference {#reference}

Neither form takes parameters — only conventions:

| Spelling | Where | Description |
| --- | --- | --- |
| `{.steps}` | line below the ordered list | Required; has no effect on an unordered list |
| `1.` | every item | Let Markdown count; the content indent is always three spaces |
| `4.` (first item) | first item | Emits `<ol start="4">` and continues from 4; supported for 2–40 |
| `{{%/* steps */%}}` | around a set of headings | Direct child headings (`##`–`######`) are the steps; the body is not indented |
{.fields meta="-"}

## Limits {#limits}

- No `{{%/* … */%}}` inside a list item: the multi-line output of a percent
  shortcode truncates the list. To put a container in a step, switch the whole
  procedure to the shortcode form.
- `{{%/* steps */%}}` cannot go inside a list item, nor inside another percent
  container.
- The marker must touch the list: no blank line between the list and
  `{.steps}`. Wrap it in `<!-- prettier-ignore-start -->` /
  `<!-- prettier-ignore-end -->` when a formatter like Prettier is in play.
- `{.steps}` applies to ordered lists only: on a `-` list there are no numbers.
- Steps do not fold and do not track progress: no "done" state, no expanding or
  collapsing.

## Related {#related}

- [Tabs](/docs/tabs/) — commands split per platform
- [Callouts](/docs/callout/) — prerequisites and warnings inside a step
- [Code blocks](/docs/code/) — the commands in a step
- [Cards](/docs/cards/) — "what next" once the procedure is done
