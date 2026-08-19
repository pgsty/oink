---
title: Infographic
linkTitle: Infographic
description: 用 `infographic` 围栏挑一个 AntV 模板，把标题与条目渲染成流程、时间线、漏斗、网格或层级信息图。
icon: fa-solid fa-shapes
weight: 160
search_keywords: [Infographic, 信息图, AntV, 流程图, 时间线, 漏斗, timeline, funnel, 模板, template]
---

`infographic` 围栏挑一个 AntV 模板，把「标题 + 一串条目」渲染成信息图。适用于表达顺序、层级与对比这类结构。需要坐标轴与数值精度时用 [ECharts](/zh/docs/echarts/)，需要条件分支的流程时用 [Mermaid](/zh/docs/mermaid/)。围栏正文是数据，在 GitHub 上仍是一段可读的文本。

## 最简例子 {#minimal}

第一行是 `infographic 模板名`，其后是一个 `data` 块：`title` 是标题，`items` 下面每个条目至少要有 `label`。

````markdown {title="源码"}
```infographic
infographic list-row-simple-horizontal-arrow
data
  title 一次文档改动的三步
  items
    - label 写
      desc 先写中文 .zh.md
    - label 校
      desc 构建零告警，例子真渲染
    - label 发
      desc 补英文对等页，提交 PR
```
````

```infographic
infographic list-row-simple-horizontal-arrow
data
  title 一次文档改动的三步
  items
    - label 写
      desc 先写中文 .zh.md
    - label 校
      desc 构建零告警，例子真渲染
    - label 发
      desc 补英文对等页，提交 PR
```

缩进决定结构，两个空格一级。标签要短，说明放 `desc`。

## 时间线 {#timeline}

`sequence-timeline-*` 系列把条目排成一条时间轴，`label` 是时间点，`desc` 是事件。

````markdown {title="源码"}
```infographic {height="420px"}
infographic sequence-timeline-simple
data
  title PostgreSQL 近五个大版本
  items
    - label 2021
      desc 14：并行查询与逻辑复制的一轮改进
    - label 2022
      desc 15：MERGE 语句
    - label 2023
      desc 16：逻辑复制可以从备库进行
    - label 2024
      desc 17：增量备份与 JSON_TABLE
    - label 2025
      desc 18：异步 IO 子系统
```
````

```infographic {height="420px"}
infographic sequence-timeline-simple
data
  title PostgreSQL 近五个大版本
  items
    - label 2021
      desc 14：并行查询与逻辑复制的一轮改进
    - label 2022
      desc 15：MERGE 语句
    - label 2023
      desc 16：逻辑复制可以从备库进行
    - label 2024
      desc 17：增量备份与 JSON_TABLE
    - label 2025
      desc 18：异步 IO 子系统
```

## 漏斗 {#funnel}

`sequence-funnel-simple` 画逐步收窄的阶段。下面是主题的五个发布状态：互不等价，走完最后一个才是上线。

````markdown {title="源码"}
```infographic {height="420px"}
infographic sequence-funnel-simple
data
  title 一次主题发布要经过的五个状态
  items
    - label 源码完成
      desc 代码写完，仅此而已
    - label 已验证
      desc 主题检查脚本与站点测试套件全绿
    - label 已发布
      desc 不可变的签名标签，能从 Go 代理拉到
    - label 已文档化
      desc 文档站钉住了这个标签
    - label 已部署
      desc 生产环境运行的就是这个版本
```
````

```infographic {height="420px"}
infographic sequence-funnel-simple
data
  title 一次主题发布要经过的五个状态
  items
    - label 源码完成
      desc 代码写完，仅此而已
    - label 已验证
      desc 主题检查脚本与站点测试套件全绿
    - label 已发布
      desc 不可变的签名标签，能从 Go 代理拉到
    - label 已文档化
      desc 文档站钉住了这个标签
    - label 已部署
      desc 生产环境运行的就是这个版本
```

## 网格卡片 {#grid}

条目之间没有先后关系时用 `list-grid-*`，它把条目排成网格而不是队列。

````markdown {title="源码"}
```infographic {height="380px"}
infographic list-grid-compact-card
data
  title 同一页内容的四种输出
  desc 每个内容组件都要在这四态里给出可用的结果
  items
    - label HTML
      desc 交互式，按需加载运行时
    - label 打印
      desc 折叠展开，去掉缩放与复制按钮
    - label Markdown
      desc 纯文本，按字节比对金样本
    - label RSS
      desc 静态，与打印同源
```
````

```infographic {height="380px"}
infographic list-grid-compact-card
data
  title 同一页内容的四种输出
  desc 每个内容组件都要在这四态里给出可用的结果
  items
    - label HTML
      desc 交互式，按需加载运行时
    - label 打印
      desc 折叠展开，去掉缩放与复制按钮
    - label Markdown
      desc 纯文本，按字节比对金样本
    - label RSS
      desc 静态，与打印同源
```

## 带数值的条目 {#values}

条目上加 `value`，能表达比例的模板（饼、环、进度）会用到它。

````markdown {title="源码"}
```infographic {height="400px"}
infographic chart-pie-donut-plain-text
data
  title 29 个 shortcode 的构成
  items
    - label 核心组件
      value 14
    - label Book 编号与索引
      value 10
    - label 发布与下载
      value 3
    - label OpenAPI
      value 2
```
````

```infographic {height="400px"}
infographic chart-pie-donut-plain-text
data
  title 29 个 shortcode 的构成
  items
    - label 核心组件
      value 14
    - label Book 编号与索引
      value 10
    - label 发布与下载
      value 3
    - label OpenAPI
      value 2
```

## 层级与手绘风格 {#hierarchy-and-theme}

条目下面可以再嵌 `children`，`hierarchy-mindmap-*` 把它画成两层的结构图。顶层的 `theme` 块换整张图的风格，`type` 取 `light`、`dark` 或 `hand-drawn`。

````markdown {title="源码"}
```infographic {height="320px"}
infographic hierarchy-mindmap-level-gradient-compact-card
theme
  type hand-drawn
data
  root
    label 主题仓库
    children
      - label layouts
        desc 模板
        children
          - label _markup
            desc 渲染钩子
          - label _partials
            desc 外壳与工具
      - label assets
        desc 资源
        children
          - label scss
            desc 令牌与组件样式
          - label js
            desc 浏览器运行时
          - label third_party
            desc 随主题分发的库
```
````

```infographic {height="320px"}
infographic hierarchy-mindmap-level-gradient-compact-card
theme
  type hand-drawn
data
  root
    label 主题仓库
    children
      - label layouts
        desc 模板
        children
          - label _markup
            desc 渲染钩子
          - label _partials
            desc 外壳与工具
      - label assets
        desc 资源
        children
          - label scss
            desc 令牌与组件样式
          - label js
            desc 浏览器运行时
          - label third_party
            desc 随主题分发的库
```

`theme` 属于 DSL，不是围栏属性。它不跟随站点的深浅色：写 `type dark` 的图在浅色页面上也是深底。两种配色模式下都要检查对比度。

## 挑模板 {#templates}

模板名是 `结构-变体` 的组合，同一个结构有多个视觉变体。常用的几类：

| 结构前缀 | 表达什么 | 例子 |
| --- | --- | --- |
| `list-row-*` `list-column-*` | 一排 / 一列并列的条目 | `list-row-simple-horizontal-arrow` |
| `list-grid-*` | 网格，条目之间无先后 | `list-grid-compact-card` `list-grid-badge-card` |
| `list-pyramid-*` `sequence-funnel-*` | 逐层收窄 | `sequence-funnel-simple` |
| `sequence-timeline-*` `sequence-roadmap-vertical-*` | 时间线与路线图 | `sequence-timeline-simple` |
| `sequence-steps-*` `sequence-snake-steps-*` | 有序步骤 | `sequence-steps-simple` |
| `compare-binary-horizontal-*` `compare-quadrant-*` | 二元对比与四象限 | `compare-binary-horizontal-simple-vs` |
| `hierarchy-mindmap-*` `hierarchy-structure-*` | 层级（配合 `children`） | `hierarchy-mindmap-level-gradient-compact-card` |
| `chart-pie-*` `chart-bar-*` `chart-column-*` | 带 `value` 的示意图 | `chart-pie-donut-plain-text` |
| `relation-network-*` `relation-dagre-flow` | 网络与流向（配合 `relations`） | `relation-dagre-flow` |

选能表达清楚关系的最小形式。完整图库见 [AntV Infographic 图库](https://infographic.antv.vision/gallery)，模板名与随主题分发的版本一一对应。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | `<div class="td-infographic">` 里一个画布容器加一段 DSL，本地 AntV 运行时画成 SVG |
| 打印 | 不画图，输出 `<pre class="td-infographic-source">` 包着的 DSL 源码 |
| Markdown | 原样保留 `infographic` 围栏与 DSL |
| RSS | 与打印相同，只有源码 |

图上的信息要在正文里写一遍：打印与 RSS 输出里只有那段 DSL。

## 参数参考 {#reference}

围栏属性行（```` ```infographic {…} ````）：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `height` | `auto` 或 CSS 长度 | `auto` | 非负数字加 `px` `rem` `em` `vh` `vw` `%`；其它写法构建失败 |
| `full` | bool | `false` | `true` 去掉正文宽度限制 |
| `class` | 空格分隔的 class | — | 透传给容器 |
{.fields meta="type default"}

`style`、`on*` 与未知属性让构建失败；空的 DSL 正文也让构建失败。

DSL 的顶层键（属于 AntV，不是主题）：

| 键 | 说明 |
| --- | --- |
| `infographic` / `template` | 模板名，第一行 |
| `data` | `title`、`desc`、`items`（也可以是 `sequences` `compares` `nodes` `values` `relations` `root`，取决于模板结构）、`order` |
| `theme` | `type`（`light` / `dark` / `hand-drawn`）、`palette`、`colorPrimary`、`stylize` 等 |
| `width` / `height` | DSL 层的画布尺寸，一般交给围栏属性 `height` |
| `design` | 逐部件的细调，少用 |
{.fields}

`items` 里每个条目可用 `label`、`desc`、`value`、`icon`、`children`、`group`、`id`。DSL 的完整定义以 [AntV Infographic 文档](https://infographic.antv.vision/learn)为准；随主题分发的版本与校验值记在主题仓库的 `VENDOR.json` 里。

## 限制与常见问题 {#limits}

- 模板名写错不会让构建失败：Hugo 只检查围栏属性，DSL 由浏览器运行时解析，模板不存在时容器里显示一行错误文字。改动模板名后在页面上确认。
- 不跟随深浅色：`theme` 写在 DSL 里，两种配色模式下都要检查对比度。
- 打印与 RSS 里只有 DSL，关键结论要写进正文。
- SVG 不是语义结构：屏幕阅读器读到的顺序未必是排版顺序。标题、列表、表格能表达的内容优先用它们。
- 标签要短：长文本在窄屏下会被截断或挤压，改动后在手机宽度下确认。

## 相关 {#related}

- [ECharts](/zh/docs/echarts/) — 需要坐标轴与精确数值时用它
- [步骤](/zh/docs/steps/) — 需要读者照做的流程用步骤
- [卡片](/zh/docs/cards/) — 可点击的入口网格
- [Mermaid](/zh/docs/mermaid/) — 带分支与条件的流程
