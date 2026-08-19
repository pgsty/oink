---
title: Mathematics
linkTitle: Mathematics
description: Inline and display mathematics with KaTeX, rendered at build time — the reader downloads no script.
icon: fa-solid fa-square-root-variable
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

## Matrices, cases and alignment {#environments}

KaTeX's environments work inside any display formula. Three of them carry most
technical writing: `bmatrix` for a statement about vectors and matrices, `cases`
for a piecewise definition, and `aligned` for a derivation that runs over several
lines. All three are build-time output — a reader on a phone downloads no more
than a reader of the sentence above.

````markdown {title="Source"}
$$
\begin{bmatrix} a^{l}_{1} \\ \vdots \\ a^{l}_{d_l} \end{bmatrix}
= \sigma\!\left(
\begin{bmatrix}
  w^{l}_{1,1} & \cdots & w^{l}_{1,d_{l-1}} \\
  \vdots      & \ddots & \vdots \\
  w^{l}_{d_l,1} & \cdots & w^{l}_{d_l,d_{l-1}}
\end{bmatrix}
\begin{bmatrix} a^{l-1}_{1} \\ \vdots \\ a^{l-1}_{d_{l-1}} \end{bmatrix}
+
\begin{bmatrix} b^{l}_{1} \\ \vdots \\ b^{l}_{d_l} \end{bmatrix}
\right)
$$
````

$$
\begin{bmatrix} a^{l}_{1} \\ \vdots \\ a^{l}_{d_l} \end{bmatrix}
= \sigma\!\left(
\begin{bmatrix}
  w^{l}_{1,1} & \cdots & w^{l}_{1,d_{l-1}} \\
  \vdots      & \ddots & \vdots \\
  w^{l}_{d_l,1} & \cdots & w^{l}_{d_l,d_{l-1}}
\end{bmatrix}
\begin{bmatrix} a^{l-1}_{1} \\ \vdots \\ a^{l-1}_{d_{l-1}} \end{bmatrix}
+
\begin{bmatrix} b^{l}_{1} \\ \vdots \\ b^{l}_{d_l} \end{bmatrix}
\right)
$$

A formula wider than the reading column scrolls inside its own viewport instead
of widening the page. In print it is static, so keep a wide matrix narrow enough
to survive a sheet of A4.

`cases` states a value that depends on which branch you are in — the shape most
latency and timeout arguments actually have:

````markdown {title="Source"}
$$
T_{\text{detect}} =
\begin{cases}
0, & \text{crash lands immediately before a probe} \\[2pt]
\tfrac{1}{2}\,t_{\text{loop}}, & \text{uniformly distributed arrival} \\[2pt]
t_{\text{loop}}, & \text{crash lands immediately after a probe}
\end{cases}
$$
````

$$
T_{\text{detect}} =
\begin{cases}
0, & \text{crash lands immediately before a probe} \\[2pt]
\tfrac{1}{2}\,t_{\text{loop}}, & \text{uniformly distributed arrival} \\[2pt]
t_{\text{loop}}, & \text{crash lands immediately after a probe}
\end{cases}
$$

`aligned` keeps a derivation on the relation it is about: the `&` marks the
column that lines up, and `\\[4pt]` adds breathing room between steps.

````markdown {title="Source"}
$$
\begin{aligned}
\delta^{l}_{j}
&= \frac{\partial C}{\partial z^{l}_{j}}
 = \sum_{k=1}^{d_{l+1}} \frac{\partial C}{\partial z^{l+1}_{k}} \frac{\partial z^{l+1}_{k}}{\partial z^{l}_{j}} \\[4pt]
&= \sigma'\bigl(z^{l}_{j}\bigr) \sum_{k=1}^{d_{l+1}} \delta^{l+1}_{k}\, w^{l+1}_{kj}
 = \sigma'\bigl(z^{l}_{j}\bigr) \Bigl[ \bigl(W^{l+1}\bigr)^{\mathsf{T}} \delta^{l+1} \Bigr]_{j}
\end{aligned}
$$
````

$$
\begin{aligned}
\delta^{l}_{j}
&= \frac{\partial C}{\partial z^{l}_{j}}
 = \sum_{k=1}^{d_{l+1}} \frac{\partial C}{\partial z^{l+1}_{k}} \frac{\partial z^{l+1}_{k}}{\partial z^{l}_{j}} \\[4pt]
&= \sigma'\bigl(z^{l}_{j}\bigr) \sum_{k=1}^{d_{l+1}} \delta^{l+1}_{k}\, w^{l+1}_{kj}
 = \sigma'\bigl(z^{l}_{j}\bigr) \Bigl[ \bigl(W^{l+1}\bigr)^{\mathsf{T}} \delta^{l+1} \Bigr]_{j}
\end{aligned}
$$

Use `aligned`, not `align`: the outer `$$` already puts KaTeX in display mode,
and the starred and unstarred `align` environments are for documents that number
their own lines.

## Formulas inside prose and tables {#inline}

An inline formula keeps the line height of the paragraph around it, so a
definition can stay in the sentence that needs it: the error of layer \(l\) is
\(\delta^{l} \equiv \partial C / \partial z^{l}\), a vector of shape
\(d_l \times 1\), and the recursion that moves it one layer back is
\(\delta^{l} = (W^{l+1})^{\mathsf{T}} \delta^{l+1} \odot \sigma'(z^{l})\).

Table cells take the same delimiters, which is how a reference table of formulas
is written — one row per equation, no images:

```markdown {title="Source"}
| Equation | What it needs | Number |
| --- | --- | :---: |
| \(\delta^{L} = \nabla_a C \odot \sigma'(z^{L})\) | The output and the label | BP1 |
```

| Equation | What it needs | Number |
| --- | --- | :---: |
| \(\delta^{L} = \nabla_a C \odot \sigma'(z^{L})\) | The output \(a^{L}\) and the label \(y\) | BP1 |
| \(\delta^{l} = \bigl(W^{l+1}\bigr)^{\mathsf{T}} \delta^{l+1} \odot \sigma'(z^{l})\) | The next layer's weights and error | BP2 |
| \(\nabla_{W^{l}} C = \delta^{l} \bigl(a^{l-1}\bigr)^{\mathsf{T}}\) | This layer's error, the previous layer's output | BP3 |
| \(\nabla_{b^{l}} C = \delta^{l}\) | This layer's error, and nothing else | BP4 |

A pipe inside a formula (`\mid`, `\vert`, `|`) ends the cell, so write
`\mid` — or `\vert` — rather than the bare character in a table.

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
