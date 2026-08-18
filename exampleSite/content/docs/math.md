---
title: Mathematics
linkTitle: Mathematics
description: Inline and display mathematics with KaTeX, rendered at build time — the reader downloads no script.
weight: 100
search_keywords: [Math, KaTeX, LaTeX, TeX, passthrough, chem, mhchem, chemistry, numbered equation, eq]
---

Mathematics is rendered by KaTeX at build time into HTML + MathML. A page with
formulas gains one local KaTeX stylesheet and nothing else — no JavaScript, no
request to a remote maths service. Inline formulas are `\(…\)`, display
formulas are `$$…$$` or `\[…\]`, and there are `math` and `chem` fences. For
TikZ drawings or macro packages KaTeX does not support, use a pre-rendered
[image](/docs/image/).

## Shortest form {#minimal}

An inline formula sits inside a sentence, with the surrounding spaces and
punctuation outside the delimiters.

```markdown {title="Source"}
The shared buffer hit ratio is \(\mathrm{hit} = \frac{H}{H + R}\), where \(H\) is `blks_hit` and \(R\) is `blks_read`.
```

The shared buffer hit ratio is \(\mathrm{hit} = \frac{H}{H + R}\), where \(H\) is `blks_hit` and \(R\) is `blks_read`.

## Display formulas {#display}

A formula in its own paragraph goes between `$$`, centred and set larger.
`\[…\]` is equivalent.

```markdown {title="Source"}
A B-tree with fan-out \(f\) over \(N\) keys has height:

$$
h = \left\lceil \log_{f} N \right\rceil
$$
```

A B-tree with fan-out \(f\) over \(N\) keys has height:

$$
h = \left\lceil \log_{f} N \right\rceil
$$

A formula too long for one line scrolls horizontally inside the reading column
rather than widening the layout; in print it stays static.

## The `math` fence {#math-fence}

The `math` fence is another way to write a display formula, and it does not
depend on the site's passthrough configuration. On GitHub the source is an
ordinary code block.

````markdown {title="Source"}
```math
N_{\text{conn}} = \lambda \cdot \bar{t}_{\text{resp}}
```
````

```math
N_{\text{conn}} = \lambda \cdot \bar{t}_{\text{resp}}
```

That is Little's law applied to a connection pool: in steady state, the
concurrency you need is the arrival rate times the mean response time. A pool is
usually far smaller than the number of clients.

## Chemistry and units {#chem}

The `chem` fence uses KaTeX's mhchem extension, and its body is written
`\ce{…}`. The same extension typesets physical units.

````markdown {title="Source"}
```chem
\ce{CO2 + H2O <=> H2CO3 <=> H+ + HCO3^-}
```
````

```chem
\ce{CO2 + H2O <=> H2CO3 <=> H+ + HCO3^-}
```

For the syntax see the [mhchem manual](https://mhchem.github.io/MathJax-mhchem/).

## Numbered equations {#numbered}

An attribute line under a display formula makes it a numbered equation. `num` is
a string the author writes (`3-1`, `5.3`) — the theme never counts — and `#id`
defaults to `eq-<num>`. The number shows to the right of the formula with a
localized "Equation" prefix.

```markdown {title="Source"}
$$
\text{WAL}_{\text{day}} \approx \text{TPS} \times \bar{s}_{\text{record}} \times 86400
$$
{#eq-wal num="3-1" caption="Estimating daily WAL volume"}

See [Equation 3-1](#eq-wal): multiply by the retention period for the floor on archive disk size.
```

$$
\text{WAL}_{\text{day}} \approx \text{TPS} \times \bar{s}_{\text{record}} \times 86400
$$
{#eq-wal num="3-1" caption="Estimating daily WAL volume"}

See [Equation 3-1](#eq-wal): multiply by the retention period for the floor on
archive disk size.

`caption` (plain text) is optional. `#id` and `caption` must appear with `num` —
there is no half-numbered equation. A duplicate ID on one page, or one number
pointing at two IDs, fails the build.

## Cross references {#xref}

The prose can reference a numbered equation with an ordinary link, as the
previous section does. For a cross-page reference, or when the "Equation N"
label should be filled in automatically, use `xref`:

```markdown {title="Source"}
Capacity planning starts from {{</* xref eq="3-1" anchor="eq-wal" /*/>}}.
```

Capacity planning starts from {{< xref eq="3-1" anchor="eq-wal" />}}.

`xref` may appear before its target; forward references are legal. For a
book-wide list of equations and the `book-equations` index, see
[publishing books](https://oink.pgsty.com/docs/write/book/).

## The `eq` shortcode {#eq-shortcode}

`eq` exists for sites that cannot enable passthrough; its body goes to the same
KaTeX renderer. Without parameters it is a display formula that registers no
number; with `num` it is equivalent to the attribute-line form above.

```markdown {title="Source"}
{{</* eq */>}}\sigma_{\text{idx}} = \frac{\text{rows}_{\text{matched}}}{\text{rows}_{\text{total}}}{{</* /eq */>}}

{{</* eq num="3-2" caption="Where a sequential scan and an index scan cost the same" */>}}
c_{\text{seq}} \cdot P = c_{\text{rand}} \cdot \sigma \cdot T
{{</* /eq */>}}
```

{{< eq >}}\sigma_{\text{idx}} = \frac{\text{rows}_{\text{matched}}}{\text{rows}_{\text{total}}}{{< /eq >}}

{{< eq num="3-2" caption="Where a sequential scan and an index scan cost the same" >}}
c_{\text{seq}} \cdot P = c_{\text{rand}} \cdot \sigma \cdot T
{{< /eq >}}

This site has passthrough on, so day-to-day writing uses `$$`. `eq` is for
migrated manuscripts and for sites that cannot change `hugo.yaml`.

## Site prerequisites {#config}

The `math` and `chem` fences need no configuration. The `$$`, `\[…\]` and
`\(…\)` delimiters depend on Goldmark's passthrough extension. Hugo does not
merge a theme's `markup` configuration, so this block has to live in the site's
own configuration file. This site uses:

```yaml {title="hugo.yaml"}
markup:
  goldmark:
    parser:
      attribute:
        block: true # numbered equations need the attribute line
    extensions:
      passthrough:
        enable: true
        delimiters:
          block: [['\[', '\]'], ['$$', '$$']]
          inline: [['\(', '\)']]
```

Every key is defined in
[Configuration](https://oink.pgsty.com/docs/customize/config/). Delimiters must
not collide with the prose: a single `$` is deliberately not configured, so a
price like "$5" is never read as mathematics.

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | KaTeX HTML + MathML rendered at build time; this page also loads a local `katex.min.css`, which pages without formulas never load |
| Print | Same as HTML, static, long formulas do not scroll |
| Markdown | The source as written: `$$` blocks with their attribute line, `math` / `chem` fences, `\(…\)`; the `eq` shortcode emits `**Equation 3-2.** caption` plus a `$$` block |
| RSS | The same static text as Markdown |

No form loads JavaScript.

## Parameter reference {#reference}

Four spellings:

| Spelling | Placement | Description |
| --- | --- | --- |
| `\(…\)` | inline | Governed by the site's passthrough configuration; takes no attributes |
| `$$…$$` / `\[…\]` | display | As above; may be followed by an attribute line to become numbered |
| ```` ```math ```` | display fence | Independent of passthrough; takes no attributes |
| ```` ```chem ```` | display fence | As above, with `\ce{…}` in the body |
{.fields}

The attribute line `{…}` under a display formula:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `num` | string | — | `[0-9A-Za-z.-]+`; registers a numbered equation and shows "Equation N" at the right |
| `#id` | identifier | `eq-<num>` | `[A-Za-z][A-Za-z0-9_.:-]*`; the anchor and cross-reference target |
| `caption` | plain text | — | Caption after the number; requires `num` |
{.fields meta="type default"}

The `eq` shortcode:

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `num` | string | — | As above; without it the formula is an unnumbered display formula |
| `id` | identifier | `eq-<num>` | Requires `num` |
| `caption` | plain text | — | Requires `num` |
| `class` | class list | — | Requires `num`; passed through for site CSS |
| Body | TeX | — | Required, non-empty |
{.fields meta="type default"}

Broken TeX — an unknown command, unbalanced braces — fails the build, and the
error carries KaTeX's message and the source position.

## Limits {#limits}

- Delimiters are a site decision: whether `$$`, `\[…\]` and `\(…\)` render
  depends solely on the passthrough extension in the site's `markup.goldmark`.
  The theme does not read a `math: true` front matter key, and without the
  configuration `$$` shows literally. The `math` fence and `eq` route around it.
- Only `$$` blocks and `eq` can be numbered: the `math` fence takes no attribute
  line, so switch spelling when you need a number.
- Numbers are hand-written: the theme neither counts nor renumbers, so
  reordering chapters means editing `num`.
- Inline formulas take no attributes: the attribute line applies to display
  formulas only.
- `caption` is plain text: Markdown inside it is not parsed.

## Related {#related}

- [Code blocks](/docs/code/) — fence attributes and numbered examples
- [Images](/docs/image/) — figures use the same `{#id num=}` numbering
- [Publishing books](https://oink.pgsty.com/docs/write/book/) — lists of equations and cross-page references
- [Configuration](https://oink.pgsty.com/docs/customize/config/) — the `markup.goldmark` keys
