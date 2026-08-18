---
title: 提示块
linkTitle: 提示块
description: 用 `> [!NOTE]` 这样的块引用写出带颜色、图标与标题的提示、警告与折叠块，不需要短代码。
weight: 10
search_keywords: [提示块, Callout, Alert, Admonition, 告警, 折叠块, note, tip, warning, caution, details]
---

提示块（Callout）是 GitHub / Obsidian 风格的块引用：`> [!TYPE]` 起头，正文跟在后面。用于把提示、警告、前提条件从正文中分离出来；正文一句话能说清的内容不必使用提示块。

## 最简例子 {#minimal}

```markdown {title="源码"}
> [!NOTE]
> Hugo Module 需要本机安装 Go；只用离线归档时不需要。
```

> [!NOTE]
> Hugo Module 需要本机安装 Go；只用离线归档时不需要。

不写标题时使用本地化的类型名（中文站显示「注意」，英文站显示 "Note"）。源码在 GitHub 上按 GitHub 的提示块渲染，在普通 Markdown 阅读器中显示为块引用，内容都不会丢失。

## 十种类型 {#types}

前五种与 GitHub 一致，后五种是 OINK 追加的语义类型。每种类型有默认图标与强调色。

```markdown {title="源码"}
> [!TIP]
> 用 `hugo server -D` 可以预览草稿。

> [!IMPORTANT]
> 主题下限是 Hugo Extended 0.160.1，低于它构建直接失败。

> [!WARNING]
> `hugo --cleanDestinationDir` 会清空 `public/`。

> [!CAUTION]
> 删除 `resources/_gen` 后第一次构建会慢很多。

> [!SUCCESS]
> 构建通过、零告警——可以推上线了。

> [!DANGER]
> 不要把 `go.work` 提交进仓库。

> [!QUESTION]
> 站点要不要开评论？看[启用评论](https://oink.pgsty.com/zh/docs/admin/comments/)。

> [!EXAMPLE]
> `pgsty.com` 就是一个只用了提示块与表格的纯文档站。

> [!QUOTE]
> Documentation is a love letter that you write to your future self.
```

> [!TIP]
> 用 `hugo server -D` 可以预览草稿。

> [!IMPORTANT]
> 主题下限是 Hugo Extended 0.160.1，低于它构建直接失败。

> [!WARNING]
> `hugo --cleanDestinationDir` 会清空 `public/`。

> [!CAUTION]
> 删除 `resources/_gen` 后第一次构建会慢很多。

> [!SUCCESS]
> 构建通过、零告警——可以推上线了。

> [!DANGER]
> 不要把 `go.work` 提交进仓库。

> [!QUESTION]
> 站点要不要开评论？看[启用评论](https://oink.pgsty.com/zh/docs/admin/comments/)。

> [!EXAMPLE]
> `pgsty.com` 就是一个只用了提示块与表格的纯文档站。

> [!QUOTE]
> Documentation is a love letter that you write to your future self.

类型名不区分大小写。

## 自定义标题 {#title}

标记同一行的后续文字是标题，支持行内 Markdown（代码、粗体、链接）。

```markdown {title="源码"}
> [!WARNING] 会改写 `public/`
> 生产构建前先确认 `baseURL` 指向正式域名，否则所有绝对链接都会指错。
```

> [!WARNING] 会改写 `public/`
> 生产构建前先确认 `baseURL` 指向正式域名，否则所有绝对链接都会指错。

## 正文内容 {#body}
正文是页面级 Markdown：列表、代码围栏、表格、图片、嵌套的提示块。每一行都以 `>` 开头，围栏也不例外。

````markdown {title="源码"}
> [!TIP] 三条命令启动预览
>
> 1. 克隆：`git clone https://github.com/pgsty/oink.pgsty.com my-docs`
> 2. 进入目录并预览：
>    ```bash
>    cd my-docs && hugo server
>    ```
> 3. 打开 <http://localhost:1313/>
>
> | 端口 | 用途 |
> | --- | --- |
> | 1313 | Hugo 开发服务器 |
````

> [!TIP] 三条命令启动预览
>
> 1. 克隆：`git clone https://github.com/pgsty/oink.pgsty.com my-docs`
> 2. 进入目录并预览：
>    ```bash
>    cd my-docs && hugo server
>    ```
> 3. 打开 <http://localhost:1313/>
>
> | 端口 | 用途 |
> | --- | --- |
> | 1313 | Hugo 开发服务器 |

## 折叠 {#collapsible}

类型后加 `-` 默认收起，加 `+` 默认展开；两者都渲染为原生 `<details>`，不加载 JavaScript。适用于完整输出、备选方案、背景说明这类不必默认展示的内容。

```markdown {title="源码"}
> [!NOTE]- 为什么需要 Go？
> Hugo 通过 Go 的模块系统下载主题（`hugo mod get`）。用 submodule 或离线归档时可以不装 Go。

> [!TIP]+ 默认展开，但读者可以收起
> 收起状态不会被记住，刷新后回到默认。
```

> [!NOTE]- 为什么需要 Go？
> Hugo 通过 Go 的模块系统下载主题（`hugo mod get`）。用 submodule 或离线归档时可以不装 Go。

> [!TIP]+ 默认展开，但读者可以收起
> 收起状态不会被记住，刷新后回到默认。

## 中性折叠块 DETAILS {#details}

`[!DETAILS]` 是没有语义颜色的折叠块：不加符号默认收起，`[!DETAILS]+` 默认展开。用于冗长输出、完整配置文件等需要折叠的内容。

````markdown {title="源码"}
> [!DETAILS] 完整的 `hugo version` 输出
> ```text
> hugo v0.164.0+extended+withdeploy darwin/arm64 BuildDate=2026-07-06T16:39:30Z VendorInfo=Homebrew
> ```
````

> [!DETAILS] 完整的 `hugo version` 输出
> ```text
> hugo v0.164.0+extended+withdeploy darwin/arm64 BuildDate=2026-07-06T16:39:30Z VendorInfo=Homebrew
> ```

## 自定义图标 {#icon}
块引用结束后的下一行写属性 `{icon="fa-solid fa-xxx"}`（一对 Font Awesome class），替换该类型的默认图标。属性行紧接块引用，中间不能有空行。

```markdown {title="源码"}
> [!TIP] PostgreSQL 18 已支持
> 从 Pigsty v4 起默认安装 PostgreSQL 18。
{icon="fa-solid fa-database"}
```

> [!TIP] PostgreSQL 18 已支持
> 从 Pigsty v4 起默认安装 PostgreSQL 18。
{icon="fa-solid fa-database"}

## 嵌套 {#nesting}

提示块可以嵌套（每层多一个 `>`），也可以放在列表项或步骤中。建议最多嵌套一层。

```markdown {title="源码"}
> [!WARNING] 升级前先备份
> 升级主题版本可能改变渲染结果。
>
> > [!TIP]- 怎么备份
> > `git tag pre-upgrade` 就够了——回滚只是 `git checkout pre-upgrade`。
```

> [!WARNING] 升级前先备份
> 升级主题版本可能改变渲染结果。
>
> > [!TIP]- 怎么备份
> > `git tag pre-upgrade` 就够了——回滚只是 `git checkout pre-upgrade`。

## 未知类型与易错写法 {#pitfalls}

未知的类型名不会导致构建失败，也不会丢失内容：该块渲染为普通块引用，`[!TYPE]` 标记原样可见。

```markdown {title="源码"}
> [!NOTICE] 这不是合法类型
> 标记会保留在页面上提醒你。
```

> [!NOTICE] 这不是合法类型
> 标记会保留在页面上提醒你。

其它常见问题：

- 正文与标题合并：经过 Prettier 等格式化工具的文件，在标题行下保留一个空的 `>` 行，否则工具会把标题并入正文。
- 属性行被格式化工具移动：把 `{icon=…}` 这类标记行放在 `<!-- prettier-ignore-start -->` / `<!-- prettier-ignore-end -->` 之间。
- `style`、`onclick` 等属性导致构建失败：属性行只接受 `icon` 与 `class`（见下表）。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | 静态类型是 `<div class="td-callout" role="note">`；折叠类型是原生 `<details>` + `<summary>` |
| 打印 | 全部静态展开，折叠块带 `data-td-callout-collapsible` 标记 |
| Markdown | 保留源码块引用（含 `[!TYPE]` 标记与标题） |
| RSS | 与打印相同，静态展开 |

提示块不加载脚本。

## 参数参考 {#reference}

标记行 `> [!TYPE]±  标题`：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `TYPE` | 枚举 | — | `NOTE` `TIP` `IMPORTANT` `WARNING` `CAUTION` `SUCCESS` `DANGER` `QUESTION` `EXAMPLE` `QUOTE` `DETAILS`；大小写不敏感；未知值渲染为普通块引用 |
| `±` | `-` / `+` / 无 | 无 | `-` 折叠默认收起，`+` 折叠默认展开；`DETAILS` 不加符号即收起 |
| 标题 | 行内 Markdown | 类型的本地化名称 | 与标记同一行 |
{.fields meta="type default"}

属性行 `{…}`（块引用之后紧接的一行）：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `icon` | Font Awesome class 对 | 类型默认图标 | 例如 `fa-solid fa-database`；`DETAILS` 默认无图标 |
| `class` | 空格分隔的 class | — | 原样透传给站点 CSS |
{.fields meta="type default"}

`style`、`on*` 与其它任何键都会让构建失败。

## 限制与常见问题 {#limits}

- 不能自定义颜色：颜色由类型决定，需要新语义时选最接近的类型并自定义标题。
- 折叠状态不持久化。
- 提示块可以放在 `{.steps}` 列表项与 `{{%/* steps */%}}` 步骤中（见[步骤](/zh/docs/steps/)），块引用的每一行都以 `>` 开头，缩进与列表项对齐。

## 相关 {#related}

- [步骤](/zh/docs/steps/) — 步骤中放置提示块
- [标签页](/zh/docs/tabs/) — 同一提示按平台分开呈现
- [编写页面](https://oink.pgsty.com/zh/docs/write/pages/) — 提示块与正文的取舍
