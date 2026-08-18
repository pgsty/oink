---
title: 文档
linkTitle: 文档
description: 写文档时可用的全部组件，一个组件一页，例子由浅入深，参数表在页尾。
icon: fa-solid fa-cubes
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
- 参数写错不会静悄悄降级，构建失败，报错带文件名与行号。
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

「形态」列的取值：原生 = Markdown 语法加属性行；围栏 = 带语言标记的代码围栏；shortcode = `{{</* … */>}}`。「运行时」列说明这个组件是否往页面上下发 JavaScript。

| 组件 | 一句话 | 最短写法 | 形态 | 运行时 |
| --- | --- | --- | --- | --- |
| [提示块](/zh/docs/callout/) | 把前提、警告与折叠说明从正文中分离 | `> [!NOTE]` | 原生 | 无 |
| [图片](/zh/docs/image/) | 图注、尺寸、缩放、编号与构建期图片处理 | `![说明](oink.webp)` | 原生 | 需站点开关 |
| [代码块](/zh/docs/code/) | 高亮、标题、复制、折叠、行链接 | ```` ```sh ```` | 围栏 | 按页加载 |
| [标签页](/zh/docs/tabs/) | 同一件事的多个平台或语言版本 | 属性行 `{tab="Linux"}` | 原生 + shortcode | 按页加载 |
| [表格](/zh/docs/table/) | 普通表格，加满宽、矩阵、标题与编号 | `{.full-width}` | 原生 | 无 |
| [参数表](/zh/docs/fields/) | 参数清单，带类型 / 必填 / 默认值芯片 | `{.fields meta="type default"}` | 原生 + shortcode | 无 |
| [步骤](/zh/docs/steps/) | 有先后的流程 | `{.steps}` | 原生 + shortcode | 无 |
| [卡片](/zh/docs/cards/) | 一组并列的去处 | `{.cards}` | 原生 + shortcode | 无 |
| [文件树](/zh/docs/filetree/) | 目录结构与对齐的注释列 | ```` ```filetree ```` | 围栏 | 按页加载 |
| [公式](/zh/docs/math/) | KaTeX 行内与块级公式 | `$$ … $$` | 原生 | 按页加载 |
| [Mermaid](/zh/docs/mermaid/) | 流程图、时序图、甘特图 | ```` ```mermaid ```` | 围栏 | 按页加载 |
| [PlantUML](/zh/docs/plantuml/) | UML 图；需要自建渲染服务 | ```` ```plantuml ```` | 围栏 | 需站点开关 |
| [思维导图](/zh/docs/markmap/) | Markdown 列表变成思维导图 | ```` ```markmap ```` | 围栏 | 需站点开关 |
| [Draw.io](/zh/docs/drawio/) | 可回编辑的图；需要自建服务 | `![说明](arch.drawio.svg)` | 原生 | 需站点开关 |
| [ECharts](/zh/docs/echarts/) | 声明式数据图表 | ```` ```echarts ```` | 围栏 | 按页加载 |
| [Infographic](/zh/docs/infographic/) | AntV 信息图 | ```` ```infographic ```` | 围栏 | 按页加载 |
| [画廊](/zh/docs/gallery/) | 一组图片共用一个缩放对话框 | ```` ```gallery ```` | 围栏 | 需站点开关 |
| [徽章](/zh/docs/badge/) | 行内状态标记 | `{{</* badge text="Beta" */>}}` | shortcode | 无 |
| [按键](/zh/docs/kbd/) | 键位与组合键 | `{{</* kbd "Ctrl" "K" */>}}` | shortcode | 无 |
| [引用](/zh/docs/include/) | 引入文件、插入站点参数、构建期注释 | `{{</* include file="parts/x.md" */>}}` | shortcode | 无 |
| [Asciinema](/zh/docs/asciinema/) | 终端录像 | `{{</* asciinema file="images/x.cast" */>}}` | shortcode | 按页加载 |

「运行时」列的四条细则：

- 代码块只在块上有复制或折叠按钮时加载 `code-block.js`；文件树只在树带注释列时加载 `filetree.js`，它负责拖动那条分栏线。
- 图片与画廊共用一个缩放对话框运行时，需要站点开启 `ui.image_zoom`，且页面上确有候选图。
- 公式在构建期由 KaTeX 渲染成 HTML 与 MathML，页面上只多一份 KaTeX 样式表与字体，没有脚本。
- `params.drawio.enable` 打开后，Draw.io 运行时在所有页面加载，不看这一页有没有用到它。

每个组件在 HTML、打印、Markdown、RSS 四种输出下都有确定形态，见各页的「输出形态」一节。
