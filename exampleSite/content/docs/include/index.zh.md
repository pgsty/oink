---
title: 引用
linkTitle: 引用
description: 用 include 插入外部文件，用 param 插入站点参数，用 comment 写不会出现在任何输出里的注释。
weight: 200
search_keywords: [引用, include, 引入文件, 片段, snippet, 复用, readfile, param, 参数, 插值, comment, 注释]
params:
  pigsty_pg_major: 18
---

三个 shortcode 各做一件事：`include` 把另一个文件的内容放进当前页面，`param` 打印一个页面或站点参数，`comment` 丢弃一段内容。适用于跨页复用的片段与散落在多页的常量：同一段安装步骤出现在三页时用 `include`，版本号出现在几十页时用 `param`，改一处即可。只在一页出现的内容写在那一页。

## 最简例子 {#minimal}

`include` 只有一个必填参数 `file`：

```markdown {title="源码"}
{{</* include file="parts/install-oink.zh.md" */>}}
```

被引的文件是一段普通 Markdown，与本页放在同一个页面包里：

````markdown {title="content/docs/include/parts/install-oink.zh.md"}
把 OINK 安装到一个已有的 Hugo 站点，三条命令：

```sh
hugo mod init github.com/you/your-site
hugo mod get github.com/pgsty/oink
hugo server
```

> [!NOTE]
> `hugo mod get` 需要本机安装 Go；用离线归档或 submodule 时不需要。

当前发布版本是 {{</* param version */>}}。
````

渲染结果与写在本页里相同：代码块有复制按钮，提示块是提示块。

{{< include file="parts/install-oink.zh.md" >}}

被引的文件不是一篇独立页面：它不出现在侧栏、不参与翻译配对、没有自己的 URL。

## 文件位置 {#sources}
`file` 按下面的顺序解析，第一个命中的胜出：

| 顺序 | 找哪里 | 写法 |
| --- | --- | --- |
| 1 | 当前页面的页面资源（页面包里的文件） | `file="config.yaml"` |
| 2 | 全局资源 `assets/` 下的文件 | `file="snippets/dsn.txt"` |
| 3 | `content/` 下的文件：`/` 开头是内容根目录，否则相对当前页面所在目录 | `file="parts/install-oink.zh.md"`、`file="/shared/notice.zh.md"` |

三处都找不到时构建失败，不输出占位内容。路径里含 `..` 也让构建失败：引用只能在 `content/` 与 `assets/` 中取文件。

引 Markdown 片段时写文件在磁盘上的真名，中文片段带 `.zh.`，如 `parts/install-oink.zh.md`。写成 `parts/install-oink.md` 也能构建通过，但会命中第 1 步：Hugo 把 `.zh.md` 资源按去掉语言后缀的名字挂在中文页上，此时 `include` 得到的是已渲染的 HTML 而不是源码，Markdown 输出里会出现 `<div class="td-code">`。非 Markdown 文件（`.yaml`、`.sh`、`.txt`）没有这个区别，两条路径取到同一份原文。

## 引入代码文件 {#code}

加 `code=true` 让文件按代码块渲染，`lang=` 指定高亮语言。引用仓库里的真实配置文件，文档与实际文件不会不一致。

```markdown {title="源码"}
{{</* include file="parts/module.zh.yml" code=true lang="yaml" */>}}
```

{{< include file="parts/module.zh.yml" code=true lang="yaml" >}}

代码块与围栏走同一条渲染管线：高亮、行号、复制按钮都有。围栏属性（`title=`、`collapse`、`hl_lines=`）传不进来，需要它们时把文件内容写成普通[代码块](/zh/docs/code/)。

## 片段内容 {#snippet-content}
片段是页面级 Markdown，在当前页面的上下文里渲染：提示块、表格、列表、图片、步骤与 shortcode 都可以用。上面那段片段结尾的「当前发布版本是 v0.5.0」，是片段里的 `{{</* param version */>}}` 在本页展开的结果。

一个片段被两页引用时，两页各自渲染一遍，各自生成标题锚点与代码块 ID，互不冲突。

> [!TIP] 适合做成片段的内容
> 安装命令、连接串、支持矩阵、法务声明：会变动、且变动时必须处处同步的内容。只在一页出现的内容写在那一页。

## 插入站点参数 {#param}

`param` 打印一个参数：先查本页 front matter，查不到再查站点配置（Hugo 的 `.Param` 规则）。

```markdown {title="源码"}
本站发布版本 {{</* param version */>}}，版权起始年 {{</* param copyright.from_year */>}}，
本页 front matter 里写了 `pigsty_pg_major: 18`，这里取到 {{</* param pigsty_pg_major */>}}。
```

本站发布版本 {{< param version >}}，版权起始年 {{< param copyright.from_year >}}，
本页 front matter 里写了 `pigsty_pg_major: 18`，这里取到 {{< param pigsty_pg_major >}}。

嵌套键用 `.` 连接，`copyright.from_year` 取的是 `params.copyright.from_year`。参数不存在、或者值是 map 与列表而不是标量时构建失败，不会留下空白。

## 在命令、表格与链接里插参数 {#param-in-place}

`param` 的输出是转义后的纯文本，可以放进代码围栏、表格单元格与链接地址。安装命令里的版本号适合这么写：

````markdown {title="源码"}
```sh
hugo mod get github.com/pgsty/oink@{{</* param tdVersion.latest */>}}
```

| 项目 | 值 |
| --- | --- |
| 当前版本 | {{</* param version */>}} |
| Hugo 下限 | {{</* param hugoMinVersion */>}} |

[发布说明](https://github.com/pgsty/oink/releases/tag/{{</* param tdVersion.latest */>}})
````

```sh
hugo mod get github.com/pgsty/oink@{{< param tdVersion.latest >}}
```

| 项目 | 值 |
| --- | --- |
| 当前版本 | {{< param version >}} |
| Hugo 下限 | {{< param hugoMinVersion >}} |

[发布说明](https://github.com/pgsty/oink/releases/tag/{{< param tdVersion.latest >}})

站点参数在哪里定义、有哪些可用，见[配置总览](https://oink.pgsty.com/zh/docs/customize/config/)；页面参数见[页面参数](https://oink.pgsty.com/zh/docs/write/frontmatter/)。

## 构建期删除的注释 {#comment}

`comment` 的内容在 HTML、打印、Markdown、RSS 四种输出里都不出现。HTML 注释不同：它留在页面源码里，也会进入 `llms.txt`。

```markdown {title="源码"}
PostgreSQL 18 起 `pg_stat_io` 拆分了 WAL 统计。

{{</* comment */>}}
待办：v0.5 发布后把上面的版本号换成 19，并补一张 pg_stat_io 的截图。
这段文字不会出现在任何输出里，包括 llms.txt。
{{</* /comment */>}}

升级前先在测试库上验证监控面板。
```

PostgreSQL 18 起 `pg_stat_io` 拆分了 WAL 统计。

{{< comment >}}
待办：v0.5 发布后把上面的版本号换成 19，并补一张 pg_stat_io 的截图。
这段文字不会出现在任何输出里，包括 llms.txt。
{{< /comment >}}

升级前先在测试库上验证监控面板。

上面两段之间有一段注释，查看页面源码也找不到它。

## 输出形态 {#outputs}

| 输出 | `include`（Markdown） | `include code=true` | `param` | `comment` |
| --- | --- | --- | --- | --- |
| HTML | 片段渲染成正常内容 | 高亮代码块 + 复制按钮 | 转义后的纯文本 | 无 |
| 打印 | 同 HTML | 同 HTML，无复制按钮 | 同 HTML | 无 |
| Markdown | 片段的源码原样输出 | 源码围栏 | 值本身 | 无 |
| RSS | 同 HTML | 同 HTML | 同 HTML | 无 |

Markdown 输出里片段是源码而不是 HTML，片段里的 shortcode 保持 `{{</* param version */>}}` 的原样。这与「Markdown 输出保留源码」一致，不是漏渲染。三个 shortcode 都不加载脚本。

## 参数参考 {#reference}

`include`（只接受具名参数）：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `file` | 路径（必填） | — | 解析顺序见[文件放在哪](#sources)；含 `..`、文件缺失、空值都构建失败 |
| `code` | 布尔 | `false` | `true` 时按代码块渲染；必须写成 `code=true`，带引号的 `code="true"` 是字符串，构建失败 |
| `lang` | 字符串 | — | 代码语言；只能与 `code=true` 同用，单独出现构建失败 |
{.fields meta="type default"}

其它任何参数名都会构建失败，报错里带文件名与行号。

`param`（一个位置参数）：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| 参数名 | 字符串（必填） | — | 嵌套键用 `.` 连接；先页面 front matter 后站点 `params`；缺失或非标量（map / 列表）构建失败 |
{.fields meta="type default"}

`comment` 没有参数，成对使用，`{{</* comment */>}}` 与 `{{</* /comment */>}}` 之间的内容整段丢弃。

## 限制与常见问题 {#limits}

- `include` 不是模板：不能向片段传变量、不能条件引入、不能给引入的代码块加围栏属性（`title=`、`collapse`）。按平台分版本时写两个片段配[标签页](/zh/docs/tabs/)。
- 片段的语言要自己维护：`include` 不做语言回退。中文页引中文片段，英文页引英文片段，两份文件并列存放（`install-oink.zh.md` 与 `install-oink.md`）。
- `param` 只打印标量：结构化数据（版本矩阵、下载列表）用 `data/` 目录里的数据配对应组件渲染。
- `comment` 不是「暂时不发布」：内容每次构建都被丢弃，临时下线整页用 `draft: true`。
- 不把 `include` 当目录页：一页引入十个片段时，读者需要的是十条链接。

## 相关 {#related}

- [代码块](/zh/docs/code/) — 围栏的全部属性，`include code=true` 用的是同一套渲染
- [标签页](/zh/docs/tabs/) — 按平台 / 语言分版本的片段
- [配置总览](https://oink.pgsty.com/zh/docs/customize/config/) — `param` 能取到的站点参数
- [页面参数](https://oink.pgsty.com/zh/docs/write/frontmatter/) — 页面级参数，优先于站点配置
