---
title: 参数表
linkTitle: 参数表
description: 用一张普通表格加 `{.fields}` 记录配置项、命令参数与 API 字段：名称、类型、默认值、说明各就各位，窄屏不挤，每条都能单独链接。
icon: fa-solid fa-sliders
weight: 60
search_keywords: [参数表, Fields, field, 配置项, 参数, API 字段, meta, type, required, default, 定义列表, 锚点]
---

参数表（Fields）把「一串具名值 + 元数据 + 说明」渲染成响应式定义列表：名称独占一行，类型、是否必填、默认值是名称旁边的小字，说明另起一行，每一条自带锚点。用于配置项、命令参数与 API 字段。要按同一批列横向比较很多行时用普通表格，内容是操作顺序时用步骤。

写法有两种：普通表格加 `{.fields}`（默认选它），以及 `fields`/`field` shortcode（说明需要多个段落、列表或代码块时才用）。两种形态渲染出相同的条目。

## 最简例子 {#minimal}

一张至少两列的管道表格，下一行写 `{.fields}`。第一列是名称，最后一列是说明，中间每一列都是元数据，标签就是表头文字本身。

```markdown {title="源码"}
| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `offline_search` | boolean | `false` | 构建本地搜索索引并启用命令面板 |
| `offline_search_max_results` | integer | `10` | 搜索结果条数上限 |
| `page_width` | string | `normal` | 正文栏宽度，可选 `narrow` `normal` `wide` |
{.fields}
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `offline_search` | boolean | `false` | 构建本地搜索索引并启用命令面板 |
| `offline_search_max_results` | integer | `10` | 搜索结果条数上限 |
| `page_width` | string | `normal` | 正文栏宽度，可选 `narrow` `normal` `wide` |
{.fields}

这里的元数据显示成「表头: 值」。主题不推断表头的含义，`类型` 只是一个标签；要让它变成标准芯片见下一节。单元格接受行内 Markdown（代码、强调、链接），空的中间单元格省略。

## 语义列 `meta=` {#meta}

`meta` 按顺序说明每一个中间列扮演什么角色：`type`（类型）、`required`（必填）、`default`（默认值），或者 `-`（保留表头当标签）。有了它，表格形态渲染出的芯片与 shortcode 形态一致。

```markdown {title="源码"}
| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `baseURL` | string | 是 | | 站点地址，含子路径 |
| `title` | string | 是 | | 站点名，出现在顶栏与页签 |
| `defaultContentLanguage` | string | | `en` | 默认语言，决定无前缀路径属于哪种语言 |
{.fields meta="type required default"}
```

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `baseURL` | string | 是 | | 站点地址，含子路径 |
| `title` | string | 是 | | 站点名，出现在顶栏与页签 |
| `defaultContentLanguage` | string | | `en` | 默认语言，决定无前缀路径属于哪种语言 |
{.fields meta="type required default"}

规则：

- `meta` 必须为每一个中间列写一个角色，个数等于总列数减二；写多写少都构建失败。
- `required` 列是「非空即真」：单元格里写「是」「yes」「✔」都一样，渲染出来的是不翻译的 `required` 芯片；留空就不显示。
- `type` 与 `default` 单元格如果本身没有行内标记，会自动套上代码格式，与 shortcode 形态对齐。
- 三种语义芯片按 `type`、`required`、`default` 的顺序显示，与列的顺序无关；`-` 列跟在后面，按列顺序排。

`-` 可以和语义角色混用，用来保留一列自定义标签：

```markdown {title="源码"}
| 环境变量 | 类型 | 作用域 | 说明 |
| --- | --- | --- | --- |
| `HUGO_MODULE_WORKSPACE` | string | 构建 | 指向 `go.work`，让主题从本地 checkout 解析 |
| `HUGO_ENV` | string | 构建 | 设为 `production` 时启用压缩与指纹 |
{.fields meta="type -"}
```

| 环境变量 | 类型 | 作用域 | 说明 |
| --- | --- | --- | --- |
| `HUGO_MODULE_WORKSPACE` | string | 构建 | 指向 `go.work`，让主题从本地 checkout 解析 |
| `HUGO_ENV` | string | 构建 | 设为 `production` 时启用压缩与指纹 |
{.fields meta="type -"}

## 标签与容器 ID {#caption-id}

`caption` 给整张表加一个可见标签（同时是无障碍名称），`id` 命名外层容器，方便从别处链接过来或写站点 CSS。

```markdown {title="源码"}
| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enable` | boolean | `false` | 打开图片缩放 |
| `selector` | string | `.td-content` | 扫描候选图片的根选择器 |
{.fields caption="params.ui.image_zoom" id="zoom-params" meta="type default"}
```

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `enable` | boolean | `false` | 打开图片缩放 |
| `selector` | string | `.td-content` | 扫描候选图片的根选择器 |
{.fields caption="params.ui.image_zoom" id="zoom-params" meta="type default"}

## 每一条都能单独链接 {#anchors}

每个条目获得一个 `field-<名称>` 形式的锚点，鼠标移上去时名称右边出现自链接图标。上面第一张表里的 `page_width` 就是 [#field-page_width](#field-page_width)，回答问题时可以把这一行的链接单独发出去。

同一页里重名的字段按 `-2`、`-3` 顺延，规则与 Goldmark 处理重名标题一致。锚点只在 HTML 里生成：打印和 RSS 会把很多页拼成一个文档，页内锚点在那里会冲突。

## shortcode 形态 {#shortcode}

说明需要多个段落、列表或代码块时，表格单元格装不下，改用 `fields`/`field`：

````markdown {title="源码"}
{{</* fields label="pig 命令常用参数" */>}}
{{</* field name="--config" type="path" required=true */>}}
配置文件路径。相对路径按当前工作目录解析。

如果同时设置了 `PIG_CONFIG` 环境变量，命令行参数优先。
{{</* /field */>}}
{{</* field name="--log-level" type="string" default="info" */>}}
日志级别，从低到高：

- `debug`：打印每一次远程调用
- `info`：默认值
- `error`：只在失败时输出
{{</* /field */>}}
{{</* field name="--dry-run" type="boolean" default=false */>}}
只打印将要执行的动作，不改任何东西：

```bash
pig ext install pg_duckdb --dry-run
```
{{</* /field */>}}
{{</* /fields */>}}
````

{{< fields label="pig 命令常用参数" >}}
{{< field name="--config" type="path" required=true >}}
配置文件路径。相对路径按当前工作目录解析。

如果同时设置了 `PIG_CONFIG` 环境变量，命令行参数优先。
{{< /field >}}
{{< field name="--log-level" type="string" default="info" >}}
日志级别，从低到高：

- `debug`：打印每一次远程调用
- `info`：默认值
- `error`：只在失败时输出
{{< /field >}}
{{< field name="--dry-run" type="boolean" default=false >}}
只打印将要执行的动作，不改任何东西：

```bash
pig ext install pg_duckdb --dry-run
```
{{< /field >}}
{{< /fields >}}

`required=true` 与 `default=false` 是布尔值，不加引号。`default` 接受任何标量：`default=0`、`default=""` 都会如实显示（空字符串显示成 `""`），不写 `default` 就不显示这一项。每个 `field` 必须有非空正文，并且必须是 `fields` 的直接子项。

## 两种形态的选择 {#which}
| 情况 | 用法 |
| --- | --- |
| 每条说明一句话，能放进表格单元格 | 表格 + `{.fields}` |
| 说明要分段、带列表或代码块 | `fields`/`field` shortcode |
| 读者需要按同一批列横向比较很多行 | 用普通表格，不转成参数表 |
| 内容是操作顺序 | 用[步骤](/zh/docs/steps/) |

表格形态在 GitHub 上仍然是一张可读的表，OINK 的 Markdown 输出也保持表格原样，这是默认选它的理由。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | `<div class="td-fields">` + 语义 `<dl>`；条目带 `#field-<名称>` 锚点与自链接 |
| 打印 | 完整定义列表，不带条目锚点 |
| Markdown | 表格形态保留源码表格；shortcode 形态输出「`名称` — 类型；required；default: 值」加缩进说明的项目符号列表 |
| RSS | 完整静态 `<dl>`，不带条目锚点 |

不加载任何脚本。

## 参数参考 {#reference}

表格属性行（写在表格下一行）：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `.fields` | 标记 | 无 | 必需；把表格渲染成参数表 |
| `meta` | 角色列表 | 无 | 空格分隔，取值 `type` `required` `default` `-`；个数等于中间列数；语义角色不可重复 |
| `caption` | 纯文本 | 无 | 可见标签，同时是列表的无障碍名称 |
| `id` | 标识符 | 无 | 外层容器的 ID |
| `class` | class 列表 | 无 | 透传给站点 CSS |
| `data-*` / `aria-*` | 字符串 | 无 | 透传 |
{.fields meta="type default"}

`fields` shortcode：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `label` | 非空字符串 | 否 | 可见标签，作用同表格的 `caption` |
| `id` | 标识符 | 否 | 外层容器 ID；不能含空白、引号、`<`、`>`、`&` |
| `class` / `data-*` / `aria-*` | 字符串 | 否 | 与表格属性行同一套策略 |
{.fields meta="type required"}

`field` shortcode：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `name` | 非空字符串 | 是 | 字段名 |
| `type` | 非空字符串 | 否 | 类型标签，如 `boolean` `string[]` `duration` |
| `required` | 布尔 | 否 | `true` 时显示不翻译的 `required` 芯片，默认 `false` |
| `default` | 标量 | 否 | 字符串 / 布尔 / 整数 / 浮点；`false`、`0`、`""` 都会显示 |
{.fields meta="type required"}

## 限制与常见问题 {#limits}

- 第一列必须非空，且在同一张表内唯一：重名或空名构建失败。
- `.fields` 不能与 `.matrix`、`.full-width`、`num` 组合，`meta` 不能用在没有 `.fields` 的表上。
- 表格单元格里放不下块内容：需要段落、列表、围栏就换 shortcode 形态。
- `required` 与 `default` 是不翻译的 API 词汇，在所有语言下都显示英文，它们是契约词，不是界面文案。
- 暂不支持 `kind`、`since`、`deprecated`、`location`、字段级链接与嵌套结构，也不会在构建时解析 TypeScript 或 OpenAPI schema。

## 相关 {#related}

- [表格](/zh/docs/table/) — 属性行的其它取值与互斥规则
- [配置总览](https://oink.pgsty.com/zh/docs/customize/config/) — 站点参数全表就是用参数表写的
- [页面参数](https://oink.pgsty.com/zh/docs/write/frontmatter/) — front matter 全表
- [步骤](/zh/docs/steps/) — 顺序动作不要写成参数表
