---
title: 代码块
linkTitle: 代码块
description: 普通 Markdown 围栏加一行属性，就得到文件名标题、精确复制、行号、高亮、换行、折叠与可链接的行。
weight: 30
search_keywords: [代码块, Code Block, 围栏, fence, 复制, copy, 行号, lineNos, 高亮, hl-lines, 折叠, collapse, 换行, wrap, Chroma, 语法高亮]
---

代码块是普通的 Markdown 围栏，高亮由 Hugo 内置的 Chroma 在构建期完成，浏览器里没有高亮器。用于命令、配置片段与源码：围栏信息行上的 `{…}` 属性决定标题栏、复制行为、行号与行锚点。图示类围栏（`mermaid`、`echarts`、`filetree` 等）不走这条路径，它们各有渲染钩子。

## 最简例子 {#minimal}

````markdown {title="源码"}
```sql
SELECT datname, numbackends FROM pg_stat_database ORDER BY numbackends DESC;
```
````

```sql
SELECT datname, numbackends FROM pg_stat_database ORDER BY numbackends DESC;
```

没有属性的围栏同样有完整外壳与复制按钮。无标题栏时不渲染空白横条，复制按钮浮在右上角，鼠标悬停或焦点进入块内时出现，触屏设备上始终可见。外壳不显示语言名，lexer 名字只写入 `data-language`，供样式表与测试使用。

语言标记就是 Chroma 的 lexer 名。`diff` 围栏用 Chroma 的增删行样式呈现补丁，不需要额外组件：

````markdown {title="源码"}
```diff {title="hugo.yaml 的改动"}
 params:
   ui:
-    sidebar_menu_compact: true
+    sidebar_menu_compact: false
     sidebar_menu_foldable: true
```
````

```diff {title="hugo.yaml 的改动"}
 params:
   ui:
-    sidebar_menu_compact: true
+    sidebar_menu_compact: false
     sidebar_menu_foldable: true
```

## 文件名标题 {#title}

`title` 给块加一条可见标题栏，通常写文件名或路径。它同时成为这个块的无障碍名称。

````markdown {title="源码"}
```yaml {title="hugo.yaml"}
markup:
  goldmark:
    parser:
      attribute:
        block: true
    renderer:
      unsafe: true
```
````

```yaml {title="hugo.yaml"}
markup:
  goldmark:
    parser:
      attribute:
        block: true
    renderer:
      unsafe: true
```

`filename` 是 `title` 的历史别名，两个一起写会构建失败。

## 行号、起始行与高亮 {#line-numbers}

`lineNos` 取 `inline`（行号与代码同一列）或 `table`（行号独立成列，可单独选中不被复制）。`lineNoStart` 改显示的起始编号。`hl_lines` 标记要强调的行，计数按围栏内的源码行，从 1 开始，与 `lineNoStart` 无关。

````markdown {title="源码"}
```ini {title="postgresql.conf" lineNos="inline" lineNoStart=120 hl_lines="2 4-5"}
shared_buffers = 8GB
max_connections = 200
work_mem = 64MB
wal_level = replica
max_wal_senders = 10
```
````

```ini {title="postgresql.conf" lineNos="inline" lineNoStart=120 hl_lines="2 4-5"}
shared_buffers = 8GB
max_connections = 200
work_mem = 64MB
wal_level = replica
max_wal_senders = 10
```

`lineNos="table"` 把行号放进独立的一列（两种模式下复制按钮都会剔除行号）：

````markdown {title="源码"}
```bash {title="部署三条命令" lineNos="table"}
./configure -c rich
./install.yml
pig ext install pg_duckdb
```
````

```bash {title="部署三条命令" lineNos="table"}
./configure -c rich
./install.yml
pig ext install pg_duckdb
```

`tabWidth` 决定制表符展开成几个空格，与 `style` 一样原样转交 Chroma。本站使用基于 class 的 Chroma 调色板（深浅色各一套），`style` 只在把 Hugo 切回内联样式模式时才生效。

## 长行换行 {#wrap}

`wrap=true` 只改变显示：源码不变，复制出来的文本也不变。不加它时长行横向滚动。

````markdown {title="源码"}
```text {title="config/artifacts.env" wrap=true}
ARTIFACT_URL=https://repo.pigsty.io/pkg/infra/v3.6.0/infra-pkg-v3.6.0.el9.x86_64.tgz
CHECKSUM=sha256:6d3dce4f7acb18f586469adcb80ab35f3e859f9837786e151cfbc2b3c0f587b2
```
````

```text {title="config/artifacts.env" wrap=true}
ARTIFACT_URL=https://repo.pigsty.io/pkg/infra/v3.6.0/infra-pkg-v3.6.0.el9.x86_64.tgz
CHECKSUM=sha256:6d3dce4f7acb18f586469adcb80ab35f3e859f9837786e151cfbc2b3c0f587b2
```

`wrap=true` 与表格行号不能共存：行号列与代码列是两个表格单元格，换行后会错位。写在一起构建失败，报错提示改用 `lineNos="inline"` 或去掉换行。

## 折叠长代码 {#collapse}

`collapse=N` 让块初始只显示 N 行，底部给一个「显示全部 N 行」按钮。服务器输出完整代码，折叠是浏览器量出第 N 行位置后的视觉裁切：没有 JavaScript 时、读屏器中、打印时代码都是完整的。

````markdown {title="源码"}
```yaml {title="hugo.yaml" collapse=8}
baseURL: https://oink.pgsty.com/
title: OINK
defaultContentLanguage: en
languages:
  en:
    languageName: English
    weight: 1
  zh:
    languageName: 简体中文
    weight: 2
params:
  offline_search: true
  ui:
    sidebar_menu_foldable: true
```
````

```yaml {title="hugo.yaml" collapse=8}
baseURL: https://oink.pgsty.com/
title: OINK
defaultContentLanguage: en
languages:
  en:
    languageName: English
    weight: 1
  zh:
    languageName: 简体中文
    weight: 2
params:
  offline_search: true
  ui:
    sidebar_menu_foldable: true
```

行数不超过 `collapse` 时按钮不出现。换行与折叠可以一起用：折叠测量的是第 N 个源码行节点的底边，换行的行不会被截断。

## 复制内容 {#copy}
默认复制整块源码。终端会话（`console` 与 `shell-session` 两个 lexer）默认只复制命令：带提示符的行留下，提示符本身与输出行去掉。下面这个块复制出来只有两条命令，没有 `$` 也没有输出。

````markdown {title="源码"}
```console
$ pig ext list duckdb
name       version  category
pg_duckdb  1.0.0    OLAP
$ pig ext install pg_duckdb
INFO installing pg_duckdb
```
````

```console
$ pig ext list duckdb
name       version  category
pg_duckdb  1.0.0    OLAP
$ pig ext install pg_duckdb
INFO installing pg_duckdb
```

要连提示符与输出一起复制就写 `copy="all"`。把 `copy="command"` 用在 `bash`、`sh` 之类普通 lexer 上会构建失败，因为它们分不出提示符、命令与输出。多行命令请在续行里写出续行提示符（通常是 `>`），否则那一行会被当成输出而排除。

会话 lexer 的块里一行提示符都没有时，复制按钮报失败：图标转为错误状态，控制台留一条错误，剪贴板不变。它不会退化成复制全文。

`copy=false` 关掉这一块的复制按钮，用于不应被抄走的反例片段：

````markdown {title="源码"}
```yaml {title="反例：属性行离开了它的块" copy=false}
params:
  ui:
    image_zoom: true   # 错：image_zoom 是一张表，不是布尔值
```
````

```yaml {title="反例：属性行离开了它的块" copy=false}
params:
  ui:
    image_zoom: true   # 错：image_zoom 是一张表，不是布尔值
```

整站关掉复制用 `params.ui.code_copy: false`，它优先于每个块自己写的 `copy`（见[配置总览](https://oink.pgsty.com/zh/docs/customize/config/)）。复制按钮只有图标，成功与失败会换图标并播报本地化状态；复制内容保留缩进、空行与 Unicode，去掉行号，末尾只留一个换行。

## 行链接与稳定 ID {#line-links}

把「看第 3 行」做成链接需要两步：给围栏一个明确的 `id`，再打开 `anchorLineNos=true`。行号随即变成锚点链接，锚点是 `#<id>-<行号>`。

````markdown {title="源码"}
```sql {id="ex-explain" title="explain.sql" lineNos="table" anchorLineNos=true}
EXPLAIN (ANALYZE, BUFFERS)
SELECT relname, n_live_tup
FROM pg_stat_user_tables
WHERE n_live_tup > 1000
ORDER BY n_live_tup DESC;
```

跳到 [第 4 行](#ex-explain-4)。
````

```sql {id="ex-explain" title="explain.sql" lineNos="table" anchorLineNos=true}
EXPLAIN (ANALYZE, BUFFERS)
SELECT relname, n_live_tup
FROM pg_stat_user_tables
WHERE n_live_tup > 1000
ORDER BY n_live_tup DESC;
```

跳到 [第 4 行](#ex-explain-4)。

不写 `id` 时主题也会生成一个页面内唯一的 ID，但它依赖围栏在页面里的顺序，前面插入一个新围栏就会变。只有作者书写的 `id` 才是永久链接。ID 不能含空白与控制字符，也不能与页面上其它块的 viewport、标签、面板、标题、行锚点 ID 重复，重复即构建失败。

## 编号例 {#numbered}

写书或长手册时给代码片段编号：`num` 加 `caption`，这个围栏就成了一条 Book「示例」目标，可以被 `xref` 引用，也会进入全书的示例目录。编号由作者书写，主题不自动计数；`id` 默认是 `eg-<num>`。

````markdown {title="源码"}
```sql {num="4-1" caption="按表统计膨胀率" #eg-bloat}
SELECT schemaname, relname, n_dead_tup, n_live_tup
FROM pg_stat_user_tables
WHERE n_dead_tup > n_live_tup * 0.2;
```

参见 {{</* xref eg="4-1" anchor="eg-bloat" */>}}。
````

```sql {num="4-1" caption="按表统计膨胀率" #eg-bloat}
SELECT schemaname, relname, n_dead_tup, n_live_tup
FROM pg_stat_user_tables
WHERE n_dead_tup > n_live_tup * 0.2;
```

参见 {{< xref eg="4-1" anchor="eg-bloat" />}}。

`num` 与 `caption` 必须成对出现，只写一个会构建失败；`num` 与标签页属性 `tab` 互斥。图、表、公式的编号写法与索引见[书籍出版](https://oink.pgsty.com/zh/docs/write/book/)。

## 一组围栏做成标签页 {#tabs}

连续几个带 `tab` 的围栏会在浏览器里合成一个标签页集，第一个围栏上的 `group` 让它可分享、可同步、可记住选择。

````markdown {title="源码"}
```bash {tab="Homebrew" group="oink-install" value="brew"}
brew install hugo
```
```bash {tab="APT" value="apt"}
sudo apt install hugo
```
````

```bash {tab="Homebrew" group="oink-install" value="brew"}
brew install hugo
```
```bash {tab="APT" value="apt"}
sudo apt install hugo
```

完整规则（分组语法、URL hash、跨组同步、正文标签页）在[标签页](/zh/docs/tabs/)。

## 易错写法 {#pitfalls}

- 在文档里展示 shortcode：围栏不阻止 Hugo 解析，写在代码块里的 `{{</* tabs */>}}` 仍会执行。要让它原样显示，在两侧定界符的内侧各加一对注释符号，写成 <code>&#123;&#123;&lt;/&#42; tabs &#42;/&gt;&#125;&#125;</code>，百分号形式对应 <code>&#123;&#123;%/&#42; steps &#42;/%&#125;&#125;</code>。本页每一处展示 shortcode 的地方都是这么写的。
- 围栏里套围栏：外层用四个反引号、内层三个，本页每一段「源码」都是这么写的；内层还有围栏时外层再加一个。
- 属性写在信息行上：围栏的属性跟在开栏那一行的语言后面，表格与图片的属性才写在块的下一行。写到下一行会变成正文里一段可见的花括号。
- 未知属性会失败，不会被忽略，错误信息里列出允许的名字。`style`、`srcdoc` 与 `on*` 被拒绝；`data-td-code*` 前缀以及 `data-language`、`data-line-count`、`data-collapse-lines` 是主题的保留名，写上去同样构建失败。
- 列表项里的围栏：缩进要与列表项内容对齐（`1.` 之后恒定三个空格），否则围栏会脱离列表。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | `<div class="td-code">` 外壳 + Chroma 的 `.highlight`/`.chroma`；复制、折叠按钮在服务器输出里是 `hidden`，脚本确认可用后才显示 |
| 打印 | 完整代码，去掉复制、折叠、渐隐；长块允许跨页；标题栏保留 |
| Markdown | 原样输出源码围栏，连 `{…}` 属性一起 |
| RSS | 静态代码块，无按钮 |

没有复制或折叠控件的页面不加载 `code-block.js`；打印、Markdown 与 RSS 输出不加载。

## 参数参考 {#reference}

开栏那一行、语言之后的 `{…}` 里，OINK 自己的属性：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `title` | 非空字符串 | 无 | 可见标题栏（通常是文件名），同时是无障碍名称 |
| `filename` | 非空字符串 | 无 | `title` 的历史别名；两者同时出现构建失败 |
| `copy` | `all` `command` `true` `false` | 会话 lexer 为 `command`，其余为 `all` | `true` 等价于 `all`；`command` 只允许 `console`/`shell-session` |
| `wrap` | 布尔 | `false` | 视觉换行，不改源码；与表格行号互斥 |
| `collapse` | 正整数 | 无 | 初始显示的最大行数；行数不足时不生效 |
| `label` | 非空字符串 | 由标题派生 | 无障碍名称，不显示在页面上；与 `aria-label` 互斥 |
| `id` | 非空 token | 自动生成 | 稳定的块 ID 与行锚点前缀；不能含空白 |
| `tab` | 非空字符串 | 无 | 标签名，见[标签页](/zh/docs/tabs/)；与 `num` 互斥 |
| `group` | `^[a-z][a-z0-9_-]*$` | 无 | 写在一组的第一个围栏上，启用 hash / 同步 / 持久化；需要 `tab` |
| `value` | `^[a-z0-9][a-z0-9_-]*$` | 无 | 分组内每个围栏必填，无分组时禁止；需要 `tab` |
| `num` | `[0-9A-Za-z.-]+` | 无 | 编号示例（Book `eg`）；必须与 `caption` 同时出现 |
| `caption` | 纯文本 | 无 | 编号示例的说明；必须与 `num` 同时出现 |
| `class` | class 列表 | 无 | 追加到 `.td-code` 根元素 |
| `data-*` / `aria-*` / `role` | 字符串 | 无 | 透传到根元素 |
{.fields meta="type default"}

`title`、`filename` 与 `label` 已经为块生成了无障碍名称与 `role="group"`。它们中的任意一个与 `aria-label`、`aria-labelledby` 或 `role` 同时出现都会构建失败；这三个属性只在块没有标题也没有 `label` 时可以透传。

同一行还能写 Chroma 选项，主题原样转交 Hugo：

| 选项 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `lineNos` | `false` `inline` `table` | `false` | 行号形态；`table` 与 `wrap=true` 互斥 |
| `lineNoStart` | 正整数 | `1` | 显示的起始行号，不影响 `hl_lines` 的计数 |
| `hl_lines` | 行号与区间 | 无 | 如 `"2 4-5"`，按围栏内源码行计数 |
| `anchorLineNos` | 布尔 | `false` | 行号变成锚点链接，前缀取自块的 `id` |
| `tabWidth` | 正整数 | Hugo 默认 | 制表符展开的空格数 |
{.fields meta="type default"}

## 限制与常见问题 {#limits}

- 不换高亮器：没有 Shiki、Twoslash、浏览器端高亮，也没有可执行的代码演练场。补丁用 `diff` 围栏，Chroma 的 `.gi`/`.gd` 就是增删行的样式。
- `copy="command"` 只认会话 lexer：写在别的语言上是构建错误，不会退化成复制全部。
- 自动生成的 ID 不是永久链接：要发链接就写 `id`。
- `mermaid`、`math`、`chem`、`markmap`、`plantuml`、`echarts`、`infographic`、`checksums`、`filetree`、`gallery` 不是代码块：它们有各自的渲染钩子，不套这层外壳，也没有复制按钮。

## 相关 {#related}

- [标签页](/zh/docs/tabs/) — 相邻围栏合成标签页的完整规则
- [引用](/zh/docs/include/) — 把仓库里的真实文件当代码块插进来
- [书籍出版](https://oink.pgsty.com/zh/docs/write/book/) — 编号示例、交叉引用与示例目录
- [打印支持](https://oink.pgsty.com/zh/docs/customize/print/) — 长代码在打印里的形态
