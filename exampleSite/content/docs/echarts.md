---
title: ECharts
linkTitle: ECharts
description: Write ECharts options as YAML or JSON in an `echarts` fence; Hugo validates them at build time and the browser draws a theme-aware chart with the local ECharts.
weight: 150
search_keywords: [ECharts, chart, bar, line, pie, height, theme, OinkEchartsFunctions]
---

The body of an `echarts` fence is an ECharts option object in YAML or JSON — not
code. Use it for quantitative charts that need axes, series and a legend. For
relationships and flows use [Mermaid](/docs/mermaid/); for order and
hierarchy use [Infographic](/docs/infographic/). Hugo parses the
options at build time and fails the build if they do not parse; the browser
draws with the ECharts copy the theme ships, and only a page that uses it loads
the runtime.

## Shortest form {#minimal}

A bar chart needs three parts: `xAxis`, `yAxis`, `series`. Below is how many
pages each of the six documentation sections has.

````markdown {title="Source"}
```echarts {height="320px"}
tooltip:
  trigger: axis
xAxis:
  type: category
  data: [Introduction, Get started, Authoring, Components, Customization, Operations]
yAxis:
  type: value
  name: pages
series:
  - name: pages
    type: bar
    data: [4, 3, 8, 22, 15, 7]
```
````

```echarts {height="320px"}
tooltip:
  trigger: axis
xAxis:
  type: category
  data: [Introduction, Get started, Authoring, Components, Customization, Operations]
yAxis:
  type: value
  name: pages
series:
  - name: pages
    type: bar
    data: [4, 3, 8, 22, 15, 7]
```

Both formats are accepted; YAML needs no quotes or commas and is shorter to
write. Broken indentation, or a body that parses to an array instead of a map,
fails the build on that line rather than emitting a blank chart.

## Multiple line series {#line}

`series` is an array, so another entry is another line, and `legend` lets the
reader hide one. Below are the release years of PostgreSQL major versions and
the end-of-support years implied by the community's five-year policy.

````markdown {title="Source"}
```echarts {height="360px"}
tooltip:
  trigger: axis
legend:
  data: [Released, End of support]
grid:
  left: 56
  right: 24
  top: 48
  bottom: 40
xAxis:
  type: category
  name: major version
  data: ["9.6", "10", "11", "12", "13", "14", "15", "16", "17", "18"]
yAxis:
  type: value
  min: 2015
  max: 2031
  name: year
series:
  - name: Released
    type: line
    smooth: false
    data: [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
  - name: End of support
    type: line
    lineStyle:
      type: dashed
    data: [2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]
```
````

```echarts {height="360px"}
tooltip:
  trigger: axis
legend:
  data: [Released, End of support]
grid:
  left: 56
  right: 24
  top: 48
  bottom: 40
xAxis:
  type: category
  name: major version
  data: ["9.6", "10", "11", "12", "13", "14", "15", "16", "17", "18"]
yAxis:
  type: value
  min: 2015
  max: 2031
  name: year
series:
  - name: Released
    type: line
    smooth: false
    data: [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
  - name: End of support
    type: line
    lineStyle:
      type: dashed
    data: [2021, 2022, 2023, 2024, 2025, 2026, 2027, 2028, 2029, 2030]
```

Quote the version numbers: unquoted `10` is a number in YAML and so is `9.6`,
but as category-axis labels they have to be strings.

## Pie and doughnut charts {#pie}

Give `radius` two values for a doughnut. Below is how OINK's 29 shortcodes break
down by purpose.

````markdown {title="Source"}
```echarts {height="340px"}
tooltip:
  trigger: item
  formatter: "{b}: {c} ({d}%)"
legend:
  bottom: 0
series:
  - type: pie
    radius: [42%, 70%]
    itemStyle:
      borderRadius: 6
      borderWidth: 2
    label:
      formatter: "{b} {c}"
    data:
      - { value: 14, name: Core components }
      - { value: 10, name: Book numbering and indexes }
      - { value: 3, name: Releases and downloads }
      - { value: 2, name: OpenAPI }
```
````

```echarts {height="340px"}
tooltip:
  trigger: item
  formatter: "{b}: {c} ({d}%)"
legend:
  bottom: 0
series:
  - type: pie
    radius: [42%, 70%]
    itemStyle:
      borderRadius: 6
      borderWidth: 2
    label:
      formatter: "{b} {c}"
    data:
      - { value: 14, name: Core components }
      - { value: 10, name: Book numbering and indexes }
      - { value: 3, name: Releases and downloads }
      - { value: 2, name: OpenAPI }
```

`{b}`, `{c}` and `{d}` are ECharts template placeholders — name, value,
percentage. Writing them in a string is enough; no function is needed.

## Height and full width {#size}

`height` defaults to `400px` and accepts `px rem em vh vw %`. `full=true` drops
the reading-column limit so the chart fills the content area, which suits charts
with many points or long labels.

````markdown {title="Source"}
```echarts {height="260px" full=true}
tooltip:
  trigger: axis
grid:
  left: 40
  right: 16
  top: 24
  bottom: 32
xAxis:
  type: category
  data: [i18n, taxonomy, font tokens, content contracts, navigation, runtime, sidebar icons, search, actions, palette, params, reading, release assets, download, landing, book, migrations, keyboard, shell, output, goldens]
yAxis:
  type: value
  name: scripts
series:
  - type: bar
    data: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
```
````

```echarts {height="260px" full=true}
tooltip:
  trigger: axis
grid:
  left: 40
  right: 16
  top: 24
  bottom: 32
xAxis:
  type: category
  data: [i18n, taxonomy, font tokens, content contracts, navigation, runtime, sidebar icons, search, actions, palette, params, reading, release assets, download, landing, book, migrations, keyboard, shell, output, goldens]
yAxis:
  type: value
  name: scripts
series:
  - type: bar
    data: [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
```

An invalid height (`360`, `36pt`) fails the build rather than falling back to
the default.

## Light and dark {#theme}

Without `theme`, a chart initializes in the reader's current colour scheme and
redraws in place when that changes — no page reload. It resizes automatically
when its container does. Switch this page to dark and the ground and text of
every chart above change with it.

A fixed `theme` pins the colours in both modes:

````markdown {title="Source"}
```echarts {height="240px" theme="dark"}
xAxis:
  type: category
  data: [HTML, Print, Markdown, RSS]
yAxis:
  type: value
series:
  - type: bar
    data: [1, 1, 1, 1]
```
````

```echarts {height="240px" theme="dark"}
xAxis:
  type: category
  data: [HTML, Print, Markdown, RSS]
yAxis:
  type: value
series:
  - type: bar
    data: [1, 1, 1, 1]
```

`dark` is the only theme built into the runtime; any other ECharts theme has to
be registered with `echarts.registerTheme()` before it can be named here.
Without a branding requirement, leave `theme` out and let the chart follow the
site.

## Callbacks with `$fn:` {#callbacks}

A fence is data and cannot carry JavaScript. When an option needs a function — a
tooltip formatter, a data-driven colour — write the string `"$fn:name"` in the
options and register that name on `window.OinkEchartsFunctions`:

````markdown {title="Source"}
<script>
  window.OinkEchartsFunctions = window.OinkEchartsFunctions || {};
  window.OinkEchartsFunctions.pageShare = function (params) {
    var p = params[0];
    return p.name + ': ' + p.value + ' pages, ' + Math.round((p.value / 59) * 100) + '% of the site';
  };
</script>

```echarts {height="300px"}
tooltip:
  trigger: axis
  formatter: "$fn:pageShare"
xAxis:
  type: category
  data: [Introduction, Get started, Authoring, Components, Customization, Operations]
yAxis:
  type: value
series:
  - type: bar
    data: [4, 3, 8, 22, 15, 7]
```
````

<script>
  window.OinkEchartsFunctions = window.OinkEchartsFunctions || {};
  window.OinkEchartsFunctions.pageShare = function (params) {
    var p = params[0];
    return p.name + ': ' + p.value + ' pages, ' + Math.round((p.value / 59) * 100) + '% of the site';
  };
</script>

```echarts {height="300px"}
tooltip:
  trigger: axis
  formatter: "$fn:pageShare"
xAxis:
  type: category
  data: [Introduction, Get started, Authoring, Components, Customization, Operations]
yAxis:
  type: value
series:
  - type: bar
    data: [4, 3, 8, 22, 15, 7]
```

Hover any bar and the tooltip is the sentence that function builds. An
unregistered name resolves to `undefined`, the chart is drawn as if the option
were not set, and neither the build nor the runtime complains. Keep the script
next to the fence so they change together.

That script is site code and deserves code review. Formatting a string template
(`{b}`, `{c}`, `{d}`) can express does not need a function.

## Where the data lives {#data}

A fence body is a literal. Hugo does not expand shortcodes, front matter
variables or files under `data/` inside it — the numbers are written in the
fence. The cost is that data cannot be shared; the benefit is that the chart and
its data go into Git together and a diff shows which number moved.

Do not draw data that changes often (version matrices, asset lists). Use a
[table](/docs/table/) or the `data/`-driven components on a
[release page](https://oink.pgsty.com/docs/write/releases/).

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | A canvas container inside `<div class="td-echarts">` plus an `application/json` options block; the local ECharts draws it |
| Print | No chart; the fence source inside `<pre class="td-echarts-source">` |
| Markdown | The `echarts` fence and its option source, kept as written |
| RSS | Same as print — source only |

Whatever the chart shows, say it in the prose too: print and RSS have no chart.

## Parameter reference {#reference}

The fence attribute line (```` ```echarts {…} ````):

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `height` | CSS length | `400px` | A non-negative number plus `px` `rem` `em` `vh` `vw` `%`; anything else fails the build |
| `theme` | string | unset | Pin an ECharts theme and stop following the site's colour scheme; only `dark` is built in |
| `full` | bool | `false` | `true` drops the reading-column limit and fills the content area |
| `class` | space-separated classes | — | Passed through to the container for site CSS |
{.fields meta="type default"}

`style`, `on*` and any other unknown attribute fail the build. The fence body
must parse to a YAML/JSON map; failing to parse, or parsing to an array, fails
too. The option keys themselves are ECharts', documented in the
[official option manual](https://echarts.apache.org/en/option.html).

There is no site-level parameter: ECharts needs no switch in `hugo.yaml` and
loads only where it is used.

## Limits {#limits}

- No JavaScript in the fence: bridge through `$fn:` when a function is needed,
  and remember an unregistered name resolves to `undefined` with no error.
- The fence reads no external data: `data/`, front matter and shortcodes are all
  out of reach; the numbers live in the fence.
- Print and RSS carry the source only, so the conclusion belongs in the prose.
- YAML type coercion: `10`, `9.6`, `on` and `yes` on a category axis become
  numbers or booleans and need quotes.
- Colour is not the only distinction: in a multi-series chart vary line style or
  marker shape too, and check legend contrast in both colour schemes.

## Related {#related}

- [Infographic](/docs/infographic/) — structure and order, not statistics
- [Tables](/docs/table/) — for few values that must be read exactly
- [Mermaid](/docs/mermaid/) — relationship and flow diagrams
- [Code blocks](/docs/code/) — the general rules for fence attribute lines
