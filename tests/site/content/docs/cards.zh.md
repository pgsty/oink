---
title: 卡片
linkTitle: 卡片
description: 用带 `{.cards}` 的链接列表排出导航卡片网格；需要图标、徽章、图片时改用 shortcode。
icon: fa-solid fa-id-card
weight: 80
search_keywords: [卡片, Cards, card, 链接卡片, 导航卡片, 栏目首页, section-index, 图标, 徽章]
---

卡片（Cards）是一组并列的链接：每张卡片一个链接标题加一句描述，网格随容器宽度自适应。适合栏目首页、「接下来读什么」与几条并列路径的入口。不适合排版正文段落（用普通段落）或做图片墙（用[画廊](/zh/docs/gallery/)）。

## 最简例子 {#minimal}

带 `{.cards}` 的链接列表就是卡片。链接是标题，` — ` 之后是描述。

```markdown {title="源码"}
- [快速上手](https://oink.pgsty.com/zh/docs/start/) — 克隆这个文档站，删掉不需要的页面，替换为你的站点信息。
- [创作内容](https://oink.pgsty.com/zh/docs/write/) — 页面怎么组织、front matter 有哪些键。
- [定制站点](https://oink.pgsty.com/zh/docs/customize/) — 导航、搜索、品牌、多语言。
{.cards}
```

- [快速上手](https://oink.pgsty.com/zh/docs/start/) — 克隆这个文档站，删掉不需要的页面，替换为你的站点信息。
- [创作内容](https://oink.pgsty.com/zh/docs/write/) — 页面怎么组织、front matter 有哪些键。
- [定制站点](https://oink.pgsty.com/zh/docs/customize/) — 导航、搜索、品牌、多语言。
{.cards}

整张卡片是点击热区，不只是标题文字。没有 `columns` 参数：列数由容器宽度决定，窄屏收成一列。

## 只有标题的卡片 {#title-only}

描述可以省略。一行一个链接，`{.cards}` 收尾。

```markdown {title="源码"}
- [提示块](/zh/docs/callout/)
- [标签页](/zh/docs/tabs/)
- [步骤](/zh/docs/steps/)
- [参数表](/zh/docs/fields/)
{.cards}
```

- [提示块](/zh/docs/callout/)
- [标签页](/zh/docs/tabs/)
- [步骤](/zh/docs/steps/)
- [参数表](/zh/docs/fields/)
{.cards}

## 松散列表与多段描述 {#loose}

一句话装不下时改用松散列表：链接单独一段，描述另起一段，列表项之间空一行。标题独占一行，描述在标题下方。`{.cards}` 仍然紧贴最后一段，中间 **不能有空行**。

```markdown {title="源码"}
- [页面参数](https://oink.pgsty.com/zh/docs/write/frontmatter/)

  每个页面参数在这里有唯一定义：类型、默认值、取值范围，以及讲它的那一页。

- [配置总览](https://oink.pgsty.com/zh/docs/customize/config/)

  站点参数按功能分组，同样每行反向链接到讲它的指南页。
{.cards}
```

- [页面参数](https://oink.pgsty.com/zh/docs/write/frontmatter/)

  每个页面参数在这里有唯一定义：类型、默认值、取值范围，以及讲它的那一页。

- [配置总览](https://oink.pgsty.com/zh/docs/customize/config/)

  站点参数按功能分组，同样每行反向链接到讲它的指南页。
{.cards}

## 图标与徽章 {#icon-badge}

链接列表不支持图标、徽章、图片与多段描述，这些用 `cards` / `card` shortcode。`icon` 是恰好一对 Font Awesome class，`badge` 是一段纯文本。

```markdown {title="源码"}
{{</* cards */>}}
{{</* card title="快速上手" link="https://oink.pgsty.com/zh/docs/start/" icon="fa-solid fa-rocket" badge="从这里开始" */>}}
Fork 文档站本身，十分钟内完成本地预览。
{{</* /card */>}}
{{</* card title="发布与下载页" link="https://oink.pgsty.com/zh/docs/write/releases/" icon="fa-solid fa-box-open" badge="v0.5" */>}}
一个发布 URL + 资产表 + 校验和，全部本地生成。
{{</* /card */>}}
{{</* card title="键盘导航" link="https://oink.pgsty.com/zh/docs/customize/keyboard/" icon="fa-solid fa-keyboard" */>}}
全站快捷键与焦点顺序。
{{</* /card */>}}
{{</* /cards */>}}
```

{{< cards >}}
{{< card title="快速上手" link="https://oink.pgsty.com/zh/docs/start/" icon="fa-solid fa-rocket" badge="从这里开始" >}}
Fork 文档站本身，十分钟内完成本地预览。
{{< /card >}}
{{< card title="发布与下载页" link="https://oink.pgsty.com/zh/docs/write/releases/" icon="fa-solid fa-box-open" badge="v0.5" >}}
一个发布 URL + 资产表 + 校验和，全部本地生成。
{{< /card >}}
{{< card title="键盘导航" link="https://oink.pgsty.com/zh/docs/customize/keyboard/" icon="fa-solid fa-keyboard" >}}
全站快捷键与焦点顺序。
{{< /card >}}
{{< /cards >}}

图标格式不符（不是 `fa-solid fa-xxx` 这样的一对 class）时构建失败，不会静默丢弃。

## Markdown 正文 {#markdown-body}

`card` 的正文按页面级 Markdown 渲染：行内代码、强调、链接、列表都可以。`title`、`badge` 这些参数是纯文本，不解析 Markdown。

```markdown {title="源码"}
{{</* cards */>}}
{{</* card title="Hugo Module" icon="fa-brands fa-golang" */>}}
`hugo mod get github.com/pgsty/oink`。推荐方式，升级只需改一行版本号。
{{</* /card */>}}
{{</* card title="Git Submodule" icon="fa-solid fa-code-branch" */>}}
无需安装 Go：

- `git submodule add`
- 主题落在 `themes/oink`
{{</* /card */>}}
{{</* /cards */>}}
```

{{< cards >}}
{{< card title="Hugo Module" icon="fa-brands fa-golang" >}}
`hugo mod get github.com/pgsty/oink`。推荐方式，升级只需改一行版本号。
{{< /card >}}
{{< card title="Git Submodule" icon="fa-solid fa-code-branch" >}}
无需安装 Go：

- `git submodule add`
- 主题落在 `themes/oink`
{{< /card >}}
{{< /cards >}}

不写 `link` 的卡片渲染成加粗标题，不生成链接。

## 带图片的卡片 {#image}

`image` 与 `![alt](src)` 的解析顺序一致：页面资源 → 全局资源 `assets/` → 静态路径 `/images/…` → 远程 URL。本地资源带上固有尺寸，避免加载跳版。

`image` 必须配一个替代文字来源：`image_alt="…"`（有信息的图）或 `decorative=true`（纯装饰）。两个都写、两个都不写都会构建失败。

```markdown {title="源码"}
{{</* cards */>}}
{{</* card title="OINK 文档外壳" link="https://oink.pgsty.com/zh/docs/about/features/" image="/images/oink.webp" image_alt="OINK 文档页面：侧栏、正文与目录三栏" */>}}
侧栏、正文、目录，三栏可以单独关闭。
{{</* /card */>}}
{{</* card title="发布说明" link="https://oink.pgsty.com/zh/docs/write/releases/" image="/images/releasenote.webp" decorative=true */>}}
装饰性封面：`decorative=true` 输出空 alt，读屏器会跳过它。
{{</* /card */>}}
{{</* /cards */>}}
```

{{< cards >}}
{{< card title="OINK 文档外壳" link="https://oink.pgsty.com/zh/docs/about/features/" image="/images/oink.webp" image_alt="OINK 文档页面：侧栏、正文与目录三栏" >}}
侧栏、正文、目录，三栏可以单独关闭。
{{< /card >}}
{{< card title="发布说明" link="https://oink.pgsty.com/zh/docs/write/releases/" image="/images/releasenote.webp" decorative=true >}}
装饰性封面：`decorative=true` 输出空 alt，读屏器会跳过它。
{{< /card >}}
{{< /cards >}}

卡片图片不参与[图片缩放](/zh/docs/image/#zoom)，整张卡片本身已经是链接。

## 栏目首页的自动卡片 {#section-index}

栏目首页（`_index.md`）不需要手写卡片列表：主题读子页的 `title`、`description`、`icon` 自动生成一组卡片。本站在 `hugo.yaml` 中全局启用：

```yaml {title="hugo.yaml"}
params:
  ui:
    section_index: cards # list | cards
```

单个栏目可以在自己的 front matter 里覆盖，也可以用 `cascade` 把选择推给整棵子树：

```yaml {title="content/docs/customize/_index.zh.md"}
params:
  ui:
    section_index: list
```

自动卡片与手写卡片使用同一套 `td-content-card` 样式，区别只在数据来源。栏目首页不要手写子页清单：手写清单会与侧栏不同步。要排的内容不是本栏目的子页时（例如混合站外链接、跨栏目推荐），才在正文里手写卡片。相关键的完整定义见[配置总览](https://oink.pgsty.com/zh/docs/customize/config/)。

## 两种形态的选择 {#forms}

| 你要的 | 用哪种 |
| --- | --- |
| 一句话描述的链接网格 | `{.cards}` 链接列表 |
| 图标、徽章、图片 | `cards` / `card` shortcode |
| 描述里要列表、代码、多段 | `cards` / `card` shortcode |
| 没有链接的卡片 | `cards` / `card` shortcode |
| 本栏目的子页 | 什么都不写，靠 `section_index: cards` |

链接列表在 GitHub 上仍是一个链接列表，shortcode 不是。能用原生形态时用原生形态。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | 原生形态是 `<ul class="cards">`；shortcode 形态是 `<div class="td-content-cards">` + 每张 `<article class="td-content-card">`。两者都是纯 CSS 网格，不加载脚本 |
| 打印 | 原生形态竖排，shortcode 形态收成两列；两者的单张卡片都避免跨页断开 |
| Markdown | 原生形态原样输出链接列表；shortcode 形态输出 `- [标题](链接) (徽章) — 描述` |
| RSS | 与 HTML 同样的标记（没有站点 CSS 时是一份可读的链接清单） |

## 参数参考 {#reference}

原生形态：

| 元素 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `{.cards}` | 列表属性行 | — | 写在无序列表 **之后** 的一行；只对无序列表生效 |
| 列表项首个链接 | Markdown 链接 | — | 卡片标题，同时是整张卡片的点击目标 |
| 其余内容 | Markdown | — | 描述。紧凑列表里跟在 ` — ` 后面，松散列表里另起一段 |
{.fields meta="type default"}

`card` 的参数（`cards` 自身不接受任何参数）：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `title` | 纯文本 | — | 必填，非空。卡片标题 |
| `link` | URL | — | 站内路径、相对路径、`http(s):`、`mailto:`；外链自动加 `rel="noopener"` |
| `icon` | Font Awesome class 对 | — | 例如 `fa-solid fa-rocket`；格式不符构建失败 |
| `badge` | 纯文本 | — | 标题右侧的小标签 |
| `image` | 图片来源 | — | 页面资源 / 全局资源 / 静态路径 / 远程 URL |
| `image_alt` | 纯文本 | — | 有 `image` 时与 `decorative` 二选一 |
| `decorative` | 布尔 | `false` | `true` 表示装饰图，输出空 alt |
| 正文 | Markdown | — | 卡片描述 |
{.fields meta="type default"}

没有 `cols`、`columns`、`accent`、`desc`、`color` 参数；未知参数一律构建失败。

## 限制与常见问题 {#limits}

- `{.cards}` 只认无序列表：有序列表加了这个标记不会变成卡片。
- `{.cards}` 必须紧贴列表：中间空一行、或缩进进列表项，标记被静默丢弃，构建不报错，列表仍是列表。渲染结果不是卡片时先检查这一行。
- `card` 只能待在 `cards` 里：单独使用、或放进别的 shortcode，构建失败并指出位置。
- 列数不可配：网格按容器宽度自适应，只有栏目首页的自动卡片能用 `params.ui.section_index_columns` 指定列数。
- 卡片不放长文：描述超过两行时改用正文段落或[提示块](/zh/docs/callout/)。

## 相关 {#related}

- [参数表](/zh/docs/fields/) — 同样有原生 / shortcode 两种形态
- [画廊](/zh/docs/gallery/) — 一组图片的网格
- [徽章](/zh/docs/badge/) — 行内状态标签
- [组织内容](https://oink.pgsty.com/zh/docs/write/organize/) — 栏目、权重与首页
- [配置总览](https://oink.pgsty.com/zh/docs/customize/config/) — `section_index` 等站点参数
