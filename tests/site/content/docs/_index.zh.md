---
title: 文档
linkTitle: 文档
description: Markdown 组件样例
icon: fa-solid fa-cubes
weight: 10
# LLMSFULL 是可选的全文包；front matter 的 outputs 会整体覆盖站点级 section
# 列表，所以这里重复常规格式。
outputs: [HTML, print, RSS, markdown, LLMSFULL]
search_keywords: [组件, components, 速查, cheatsheet, Markdown 语法, shortcode, 原生形态]
cascade:
  type: docs
  # 每个组件页都用同一组小节锚点（#minimal、#outputs、#reference、#limits、#related）。
  # 栏目级打印视图把子页拼在一起，且不像整书打印那样给页内 ID 加命名空间，
  # 因此这一栏不进打印聚合，避免 21 组重复 ID。
  no_print: true
---

这一栏回答一个问题：某个组件在 Markdown 里怎么写。每页的顺序相同：最简例子、逐步深入的例子、输出形态、参数表、限制。查语法见下面的速查表。

## 两种形态 {#two-forms}

组件的第一形态是 Markdown 语法本身：块引用、列表、表格、图片、围栏，加上紧跟其后的一行 `{…}` 属性。原生形态在 GitHub 与任意 Markdown 编辑器中仍然可读，Markdown 输出保留的也是源码。

原生形态表达不了的场景使用 shortcode：正文标签页、带块级描述的参数表、带图标与徽章的卡片、终端录像。规则有五条：

- 所有 shortcode 都写 `{{</* 名字 */>}}`，只有 `{{%/* steps */%}}` 用 `%` 分隔符，因为它的正文是页面级 Markdown。
- 嵌套名字（`tab`、`card`、`field`）只在各自的父 shortcode 里有效。
- 参数写错不会静悄悄降级：`hugo server` 会给出带文件名与行号的警告，并采用文档写明的安全回退；发布门禁使用 `--panicOnWarning`，同一条警告会让严格构建失败。各组件页所说的“构建失败”均指这种严格构建。
- 公开字符串参数（图注、标签、标题）一律是纯文本，不解析 Markdown。只有正文是 Markdown：`tab`、`card`、`field` 的正文，`include` 引入的文件，以及 Book 的 `fig`、`tbl`、`eg` 正文。
- 页面没用到的组件不下发运行时。脚本按这一页实际用到的组件拼成一个包，打印、Markdown 与 RSS 输出不加载任何脚本。

## 站点前置配置 {#prerequisites}

组件依赖三项 Goldmark 设置。克隆本站起步时它们已经配好，从零建站照抄以下片段：

```yaml {title="hugo.yaml"}
markup:
  goldmark:
    renderer:
      unsafe: true # 内容里的 HTML 不被剥掉
    parser:
      attribute:
        block: true # 启用 {…} 属性行
      wrapStandAloneImageWithinParagraph: false # 独立图片不再包进 <p>
```

- `renderer.unsafe: true`：Goldmark 默认丢弃内容里的原始 HTML，关闭时组件正文里嵌套的 HTML 会消失。
- `parser.attribute.block: true`：属性行的总开关。关闭时 `{.steps}`、`{caption="…"}` 只是正文里的一行字符串。
- `parser.wrapStandAloneImageWithinParagraph: false`：独立成段的图片不再包进 `<p>`，图片才能成为带图注的 figure，属性行才跟得上去。

个别组件另有前置条件：公式需要开启 Goldmark 的 passthrough，PlantUML 与 Draw.io 需要自建渲染服务，各页分别说明。完整的配置键见[配置总览](https://oink.pgsty.com/zh/docs/customize/config/)。

## 速查表 {#cheatsheet}

「最短写法」列给的是每个组件的最简语法：普通 Markdown 后跟一行属性、带语言标记的代码围栏，或者一个 shortcode。标签页、参数表、步骤、卡片另有 shortcode 写法，表里给的是原生形态。

| 组件 | 一句话 | 最短写法 |
| --- | --- | --- |
| [提示块](/zh/docs/callout/) | 把前提、警告与折叠说明从正文中分离 | `> [!NOTE]` |
| [图片](/zh/docs/image/) | 图注、尺寸、缩放、编号与构建期图片处理 | `![说明](oink.webp)` |
| [代码块](/zh/docs/code/) | 高亮、标题、复制、折叠、行链接 | ```` ```sh ```` |
| [标签页](/zh/docs/tabs/) | 同一件事的多个平台或语言版本 | 属性行 `{tab="Linux"}` |
| [表格](/zh/docs/table/) | 普通表格，加满宽、矩阵、标题与编号 | `{.full-width}` |
| [参数表](/zh/docs/fields/) | 参数清单，带类型 / 必填 / 默认值芯片 | `{.fields meta="type default"}` |
| [步骤](/zh/docs/steps/) | 有先后的流程 | `{.steps}` |
| [卡片](/zh/docs/cards/) | 一组并列的去处 | `{.cards}` |
| [文件树](/zh/docs/filetree/) | 目录结构与对齐的注释列 | ```` ```filetree ```` |
| [公式](/zh/docs/math/) | KaTeX 行内与块级公式 | `$$ … $$` |
| [Mermaid](/zh/docs/mermaid/) | 流程图、时序图、甘特图 | ```` ```mermaid ```` |
| [PlantUML](/zh/docs/plantuml/) | UML 图；需要自建渲染服务 | ```` ```plantuml ```` |
| [思维导图](/zh/docs/markmap/) | Markdown 列表变成思维导图 | ```` ```markmap ```` |
| [Draw.io](/zh/docs/drawio/) | 可回编辑的图；需要自建服务 | `![说明](arch.drawio.svg)` |
| [ECharts](/zh/docs/echarts/) | 声明式数据图表 | ```` ```echarts ```` |
| [Infographic](/zh/docs/infographic/) | AntV 信息图 | ```` ```infographic ```` |
| [画廊](/zh/docs/gallery/) | 一组图片共用一个缩放对话框 | ```` ```gallery ```` |
| [徽章](/zh/docs/badge/) | 行内状态标记 | `{{</* badge text="Beta" */>}}` |
| [按键](/zh/docs/kbd/) | 键位与组合键 | `{{</* kbd "Ctrl" "K" */>}}` |
| [引用](/zh/docs/include/) | 引入文件、插入站点参数、构建期注释 | `{{</* include file="parts/x.md" */>}}` |
| [Asciinema](/zh/docs/asciinema/) | 终端录像 | `{{</* asciinema file="images/x.cast" */>}}` |

关于运行时何时下发，四条细则：

- 代码块只在块上有复制或折叠按钮时加载 `code-block.js`；文件树只在树带注释列时加载 `filetree.js`，它负责拖动那条分栏线。
- 图片与画廊共用一个缩放对话框运行时，需要站点开启 `ui.image_zoom`，且页面上确有候选图。
- 公式在构建期由 KaTeX 渲染成 HTML 与 MathML，页面上只多一份 KaTeX 样式表与字体，没有脚本。
- Draw.io 只在渲染内容含 PNG 或 SVG 候选图的页面加载，并且每个不同的图片 URL 只检查一次。

每个组件在 HTML、打印、Markdown、RSS 四种输出下都有确定形态，见各页的「输出形态」一节。
