---
title: Mermaid
linkTitle: Mermaid
description: A `mermaid` fence turns text into flowcharts, sequence diagrams, Gantt charts, class diagrams and state diagrams — rendered locally, theme-aware, diff-friendly.
weight: 110
search_keywords: [Mermaid, flowchart, sequence, gantt, classDiagram, erDiagram, stateDiagram, diagram]
---

A `mermaid` fence renders text as a flowchart, sequence diagram, Gantt chart,
class diagram, ER diagram or state diagram. The diagram exists as source: it goes
into Git, it reviews as a diff, and search finds it. Rendering happens in the
reader's browser with the Mermaid copy the theme ships — no external service is
contacted. Diagrams that need pixel-level control belong in an SVG, used as an
[image](/docs/image/).

## Shortest form {#minimal}

````markdown {title="Source"}
```mermaid
flowchart LR
  content["content/"] --> Hugo
  config["hugo.yaml"] --> Hugo
  theme["OINK theme"] --> Hugo
  Hugo --> site["public/"]
```
````

```mermaid
flowchart LR
  content["content/"] --> Hugo
  config["hugo.yaml"] --> Hugo
  theme["OINK theme"] --> Hugo
  Hugo --> site["public/"]
```

The fence language is `mermaid` and there is no other switch. Only when the
theme sees such a fence does it add the Mermaid runtime to that page, and ten
diagrams on one page still load it once.

## Sequence diagrams {#sequence}

`sequenceDiagram` describes messages between participants over time, which suits
request paths and load order.

````markdown {title="Source"}
```mermaid
sequenceDiagram
  autonumber
  participant Reader as Reader's browser
  participant CDN as Static hosting
  participant JS as Page script bundle
  Reader->>CDN: GET /docs/mermaid/
  CDN-->>Reader: HTML (containing <pre class="mermaid">)
  Reader->>CDN: GET this page's bundle
  CDN-->>Reader: mermaid.min.js
  JS->>JS: render the fence source into SVG
  Note over JS: runtimes the page never used are not downloaded
```
````

```mermaid
sequenceDiagram
  autonumber
  participant Reader as Reader's browser
  participant CDN as Static hosting
  participant JS as Page script bundle
  Reader->>CDN: GET /docs/mermaid/
  CDN-->>Reader: HTML (containing <pre class="mermaid">)
  Reader->>CDN: GET this page's bundle
  CDN-->>Reader: mermaid.min.js
  JS->>JS: render the fence source into SVG
  Note over JS: runtimes the page never used are not downloaded
```

## Gantt charts {#gantt}

`gantt` draws intervals. Below is the five-year community support window of each
PostgreSQL major version, counted from its release date; `1825d` is five years.

````markdown {title="Source"}
```mermaid
gantt
  title Five-year community support per PostgreSQL major version
  dateFormat YYYY-MM-DD
  axisFormat %Y
  section PG 15
  released 2022-10-13 :2022-10-13, 1825d
  section PG 16
  released 2023-09-14 :2023-09-14, 1825d
  section PG 17
  released 2024-09-26 :2024-09-26, 1825d
  section PG 18
  released 2025-09-25 :active, 2025-09-25, 1825d
```
````

```mermaid
gantt
  title Five-year community support per PostgreSQL major version
  dateFormat YYYY-MM-DD
  axisFormat %Y
  section PG 15
  released 2022-10-13 :2022-10-13, 1825d
  section PG 16
  released 2023-09-14 :2023-09-14, 1825d
  section PG 17
  released 2024-09-26 :2024-09-26, 1825d
  section PG 18
  released 2025-09-25 :active, 2025-09-25, 1825d
```

## Class and ER diagrams {#class-and-er}

`classDiagram` draws types and relationships, `erDiagram` entities and
cardinality. Both are common ways to explain a data model.

````markdown {title="Source"}
```mermaid
classDiagram
  class Page {
    +string Title
    +string Description
    +int Weight
    +Content()
    +OutputFormats()
  }
  class Resource {
    +string Name
    +string RelPermalink
    +Resize(spec)
  }
  class OutputFormat {
    +string Name
    +string MediaType
  }
  Page "1" --> "0..*" Resource : page bundle resources
  Page "1" --> "1..*" OutputFormat : html / print / markdown / rss
```
````

```mermaid
classDiagram
  class Page {
    +string Title
    +string Description
    +int Weight
    +Content()
    +OutputFormats()
  }
  class Resource {
    +string Name
    +string RelPermalink
    +Resize(spec)
  }
  class OutputFormat {
    +string Name
    +string MediaType
  }
  Page "1" --> "0..*" Resource : page bundle resources
  Page "1" --> "1..*" OutputFormat : html / print / markdown / rss
```

````markdown {title="Source"}
```mermaid
erDiagram
  pg_database ||--o{ pg_namespace : "contains schemas"
  pg_namespace ||--o{ pg_class : "contains relations"
  pg_class ||--o{ pg_attribute : "has columns"
  pg_class ||--o{ pg_index : "is indexed by"
  pg_class {
    oid oid PK
    name relname
    char relkind
  }
  pg_attribute {
    oid attrelid FK
    name attname
    smallint attnum
  }
```
````

```mermaid
erDiagram
  pg_database ||--o{ pg_namespace : "contains schemas"
  pg_namespace ||--o{ pg_class : "contains relations"
  pg_class ||--o{ pg_attribute : "has columns"
  pg_class ||--o{ pg_index : "is indexed by"
  pg_class {
    oid oid PK
    name relname
    char relkind
  }
  pg_attribute {
    oid attrelid FK
    name attname
    smallint attnum
  }
```

## State diagrams {#state}

`stateDiagram-v2` draws states and the conditions between them. Below are the
five states an OINK release passes through. They are not interchangeable, and a
green local build is none of them.

````markdown {title="Source"}
```mermaid
stateDiagram-v2
  [*] --> SourceComplete
  SourceComplete --> Validated : theme checks + site suite green
  Validated --> Published : an immutable signed vX.Y.Z tag is pushed
  Published --> Documented : the site's go.mod pins that tag
  Documented --> Deployed : the production build goes live
  Deployed --> [*]
  Published --> SourceComplete : a problem means a new patch version; tags never move
```
````

```mermaid
stateDiagram-v2
  [*] --> SourceComplete
  SourceComplete --> Validated : theme checks + site suite green
  Validated --> Published : an immutable signed vX.Y.Z tag is pushed
  Published --> Documented : the site's go.mod pins that tag
  Documented --> Deployed : the production build goes live
  Deployed --> [*]
  Published --> SourceComplete : a problem means a new patch version; tags never move
```

## Per-diagram title and configuration {#per-diagram-config}

The top of a fence body may carry Mermaid's own YAML header — this is not Hugo
front matter. `title` gives the diagram a title and `config` overrides Mermaid
configuration for this diagram alone. A diagram that hard-codes `config.theme`
no longer follows the site's colour scheme.

````markdown {title="Source"}
```mermaid
---
title: Only the runtimes a page used are bundled
config:
  flowchart:
    curve: linear
---
flowchart TD
  Page --> Which{which components?}
  Which -->|Mermaid fence| M[mermaid.min.js]
  Which -->|ECharts fence| E[echarts.min.js]
  Which -->|none| B[base bundle only]
```
````

```mermaid
---
title: Only the runtimes a page used are bundled
config:
  flowchart:
    curve: linear
---
flowchart TD
  Page --> Which{which components?}
  Which -->|Mermaid fence| M[mermaid.min.js]
  Which -->|ECharts fence| E[echarts.min.js]
  Which -->|none| B[base bundle only]
```

## Light and dark {#dark-mode}

The theme reads the current colour scheme when the page initializes: in dark
mode it uses Mermaid's `dark` theme, in light mode the theme the site
configured. Mermaid cannot be re-initialized, so switching the colour scheme
**reloads the whole page** and the diagrams come back in the new colours.

For that reason, keep Mermaid diagrams off pages that must preserve input
state — a page with a form, for instance.

Site-wide defaults go in `hugo.yaml` with lowercase keys; the theme matches them
back to Mermaid's own casing:

```yaml {title="hugo.yaml"}
params:
  mermaid:
    theme: neutral
    flowchart:
      diagrampadding: 6
```

The full key table is in
[Configuration](https://oink.pgsty.com/docs/customize/config/); for accepted
values see the
[Mermaid configuration reference](https://mermaid.js.org/config/schema-docs/config.html).

## Inside tabs and steps {#compose}

A `mermaid` fence has no `tab` attribute — adjacent-fence tabs apply to ordinary
code fences only. To compare two diagrams side by side, use the `tabs`
shortcode.

````markdown {title="Source"}
{{</* tabs */>}}
{{</* tab label="By data flow" */>}}
```mermaid
flowchart LR
  Markdown --> Goldmark --> RenderHooks --> HTML
```
{{</* /tab */>}}
{{</* tab label="By output format" */>}}
```mermaid
flowchart LR
  Page --> HTML
  Page --> Print
  Page --> Markdown
  Page --> RSS
```
{{</* /tab */>}}
{{</* /tabs */>}}
````

{{< tabs >}}
{{< tab label="By data flow" >}}
```mermaid
flowchart LR
  Markdown --> Goldmark --> RenderHooks --> HTML
```
{{< /tab >}}
{{< tab label="By output format" >}}
```mermaid
flowchart LR
  Page --> HTML
  Page --> Print
  Page --> Markdown
  Page --> RSS
```
{{< /tab >}}
{{< /tabs >}}

Each step inside `{{%/* steps */%}}` is page-level Markdown and can hold a
`mermaid` fence; see [Steps](/docs/steps/).

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | `<pre class="mermaid">` plus the local Mermaid runtime; the browser draws the SVG |
| Print | Same as HTML: the print view loads the runtime too, so the diagrams are drawn |
| Markdown | The `mermaid` fence and its source, kept as written |
| RSS | The diagram source inside `<pre class="mermaid">` — subscribers see text |

## Parameter reference {#reference}

Fence attributes: none. A `mermaid` fence reads no attribute line; writing
`{height=…}` or `{class=…}` neither works nor errors. Size follows the diagram
itself and the container width.

Site parameters (`hugo.yaml`):

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `params.mermaid` | map | unset | The whole map is passed to Mermaid's `initialize()`; write keys in lowercase and the theme matches them back to Mermaid's casing |
| `params.mermaid.theme` | string | Mermaid's default | The light-mode theme; dark mode forces `dark` |
{.fields meta="type default"}

Per-diagram configuration goes in the YAML header at the top of the fence body
(`title`, `config`). That is Mermaid syntax, not a theme parameter.

## Limits {#limits}

- Switching colour scheme reloads the page: Mermaid cannot be re-initialized,
  and the theme chose correct rendering over avoiding the reload.
- Diagrams cannot be numbered or zoomed: Mermaid emits inline SVG, not an
  `<img>`, so `{#id num=}` numbering and image zoom do not apply. Export to an
  image when you need a number and use the [image](/docs/image/)
  numbering.
- Fence attributes do nothing: control width inside the diagram (flowchart
  direction, class-diagram layout) or with CSS.
- Syntax errors show up only in the browser: Hugo does not parse Mermaid, so a
  broken diagram renders Mermaid's error box while the build still passes. Check
  in a browser before publishing.
- RSS subscribers see the source only: put the conclusion in the prose, not only
  in the picture.

## Related {#related}

- [PlantUML](/docs/plantuml/) — more complete UML, at the price of a rendering server
- [Markmap](/docs/markmap/) — outline-shaped hierarchies
- [ECharts](/docs/echarts/) — charts with numbers in them
- [Images](/docs/image/) — hand-drawn SVG, numbering and zoom
