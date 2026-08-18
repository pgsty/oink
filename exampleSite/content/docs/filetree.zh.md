---
title: 文件树
linkTitle: 文件树
description: 用 `filetree` 围栏画带注释的目录结构：对齐的注释列、逐条目图标、可折叠目录、可拖动的分栏。
weight: 90
search_keywords: [文件树, FileTree, 目录树, tree, 目录结构, 仓库结构, 围栏, icon, tone, open]
---

文件树（FileTree）是一个 `filetree` 围栏，围栏正文就是目录清单：缩进表示层级，结尾的 `/` 表示目录，`#` 之后是注释。适合解释一份目录结构里与读者有关的那部分，并逐条加上说明。需要读者逐字复制的清单用普通代码块。

## 最简例子 {#minimal}

````markdown {title="源码"}
```filetree
- content/
  - _index.zh.md
  - docs/
  - blog/
- hugo.yaml
- go.mod
```
````

```filetree
- content/
  - _index.zh.md
  - docs/
  - blog/
- hugo.yaml
- go.mod
```

项目符号（`-`、`*`、`+`）可以省略，效果相同。有子项的条目是目录；没有子项时，结尾的 `/` 告诉主题它是目录。

## 加注释 {#comments}

每行第一个前面带空白的 `#` 之后是注释，渲染成对齐的右列。注释是纯文本，里面的 Markdown 按字面显示；要一个字面井号就写 `\#`。

````markdown {title="源码"}
```filetree
- content/          # 全部页面，中英双语同目录
  - docs/          # 你正在读的这棵文档树
  - blog/           # 发布说明与文章
- assets/scss/      # 站点自己的 SCSS，覆盖主题变量
- layouts/          # 站点级模板覆盖，越少越好
- static/images/    # 不需要构建期处理的图
- hugo.yaml          # 站点配置：语言、菜单、params.ui
```
````

```filetree
- content/          # 全部页面，中英双语同目录
  - docs/          # 你正在读的这棵文档树
  - blog/           # 发布说明与文章
- assets/scss/      # 站点自己的 SCSS，覆盖主题变量
- layouts/          # 站点级模板覆盖，越少越好
- static/images/    # 不需要构建期处理的图
- hugo.yaml          # 站点配置：语言、菜单、params.ui
```

注释列的起点在构建期算出，由最宽的一行决定，因此每行的 `#` 从同一列开始，与源码里是否对齐无关。注释列最多占面板的右半边，最少占三成。中间的虚线是分隔条，可以拖动，也可以用 <kbd>Tab</kbd> 聚焦后按方向键调整（<kbd>Home</kbd> / <kbd>End</kbd> 到两端）。

过长的名称与注释各自在本列内用省略号截断，鼠标悬停时由 `title` 提示完整文本。分隔条是文件树唯一的 JavaScript，只有 **带注释** 的树才加载它。

## 标题栏 {#title}

围栏属性 `{title="…"}` 在树上方渲染一条标题栏；不写时没有标题栏。

````markdown {title="源码"}
```filetree {title="oink.pgsty.com 仓库根目录"}
- content/          # 页面
- assets/           # 参与构建的资源
- data/             # 首页、Landing、下载页的数据
- layouts/          # 模板覆盖
- static/           # 原样拷贝的文件
- tests/            # Playwright 与 node --test
- hugo.yaml
- go.mod            # 用 Hugo Module 引入主题
- Makefile          # make d / make b / make c
```
````

```filetree {title="oink.pgsty.com 仓库根目录"}
- content/          # 页面
- assets/           # 参与构建的资源
- data/             # 首页、Landing、下载页的数据
- layouts/          # 模板覆盖
- static/           # 原样拷贝的文件
- tests/            # Playwright 与 node --test
- hugo.yaml
- go.mod            # 用 Hugo Module 引入主题
- Makefile          # make d / make b / make c
```

## 缩进与层级 {#indent}

层级由缩进决定。两个空格、四个空格、制表符（按四列计算）都可以，同一棵树内不要求统一，条件是每次退回的层级此前已经打开过。`tree` 命令的输出可以整段粘贴，包括开头的根目录行与结尾的统计行，统计行会被丢弃。

````markdown {title="源码"}
```filetree
content/docs
├── about
│   ├── _index.zh.md
│   └── features.zh.md
├── components
│   ├── filetree.zh.md
│   └── image
│       └── index.zh.md
└── _index.zh.md

3 directories, 5 files
```
````

```filetree
content/docs
├── about
│   ├── _index.zh.md
│   └── features.zh.md
├── components
│   ├── filetree.zh.md
│   └── image
│       └── index.zh.md
└── _index.zh.md

3 directories, 5 files
```

退回到未打开过的缩进层级时构建失败，报错里带围栏内的行号。

## 折叠与显式类型 {#dir-file}

有子项的目录默认展开，`{open=false}` 使其初始收起。目录用原生 `<details>` 渲染，键盘可操作，不需要 JavaScript。`open` 只能写在目录上。没有子项、名字也不以 `/` 结尾的条目按文件处理，`{type=dir}` 覆盖这个判断，`{type=file}` 同理。

````markdown {title="源码"}
```filetree {title="内容目录"}
- content/
  - docs/                # 新文档树
    - components/         # 22 个组件页        {open=false}
      - callout.zh.md
      - filetree.zh.md
      - image/            # 页面包：正文 + 图  {type=dir}
    - customize/          # 站点级配置          {open=false}
      - config.zh.md
  - blog/
    - release.zh.md
```
````

```filetree {title="内容目录"}
- content/
  - docs/                # 新文档树
    - components/         # 22 个组件页        {open=false}
      - callout.zh.md
      - filetree.zh.md
      - image/            # 页面包：正文 + 图  {type=dir}
    - customize/          # 站点级配置          {open=false}
      - config.zh.md
  - blog/
    - release.zh.md
```

## 图标与配色 {#icon-tone}

图标默认按名字推断：目录用文件夹图标，随开合切换；文件先按完整文件名匹配（`LICENSE`、`Makefile`、`go.mod`、`package.json`、`.gitignore` 等），再按扩展名匹配（`md yml toml json sh py go js sql css png svg pdf zip` 等），都不匹配时用普通文件图标。

`{icon=…}` 覆盖它，取值是恰好一对 Font Awesome class。`{tone=…}` 给图标上色，取值与[徽章](/zh/docs/badge/)相同：`neutral` `info` `success` `warning` `danger`。

````markdown {title="源码"}
```filetree {title="部署目录：权限与要点"}
- /etc/pigsty/                 # 0755 root:root · 配置根目录        {icon="fa-solid fa-server" tone=info}
  - pigsty.yml                 # 0644 root:root · 集群清单
  - ca/                        # 0700 root:root · 自签 CA，不要提交进 Git  {icon="fa-solid fa-lock" tone=danger open=false}
    - ca.key                   # 0600 root:root
- /var/lib/pgsql/18/data/      # 0700 postgres:postgres · 数据目录   {tone=warning}
  - postgresql.conf            # 0600 postgres:postgres
- /usr/bin/pig                 # 0755 root:root · 命令行工具         {icon="fa-solid fa-terminal" tone=success}
```
````

```filetree {title="部署目录：权限与要点"}
- /etc/pigsty/                 # 0755 root:root · 配置根目录        {icon="fa-solid fa-server" tone=info}
  - pigsty.yml                 # 0644 root:root · 集群清单
  - ca/                        # 0700 root:root · 自签 CA，不要提交进 Git  {icon="fa-solid fa-lock" tone=danger open=false}
    - ca.key                   # 0600 root:root
- /var/lib/pgsql/18/data/      # 0700 postgres:postgres · 数据目录   {tone=warning}
  - postgresql.conf            # 0600 postgres:postgres
- /usr/bin/pig                 # 0755 root:root · 命令行工具         {icon="fa-solid fa-terminal" tone=success}
```

`tone` 只给图标上色，不改文字。颜色是补充，含义写在名字或注释里。

## 条目链接 {#link}

条目名写成 `[名字](链接)` 即为链接。站内路径、相对路径、`http(s):` 都可以，URL 校验与其它组件是同一套。

````markdown {title="源码"}
```filetree {title="本站的组件页"}
- content/docs/
  - [callout.zh.md](/zh/docs/callout/)     # 提示块
  - [filetree.zh.md](/zh/docs/filetree/)   # 当前页面
  - [gallery.zh.md](/zh/docs/gallery/)     # 画廊
  - image/                                             # 页面包
    - [index.zh.md](/zh/docs/image/)       # 图片
- [hugo.yaml](https://github.com/pgsty/oink.pgsty.com/blob/main/hugo.yaml)   # 站点配置（GitHub）
```
````

```filetree {title="本站的组件页"}
- content/docs/
  - [callout.zh.md](/zh/docs/callout/)     # 提示块
  - [filetree.zh.md](/zh/docs/filetree/)   # 当前页面
  - [gallery.zh.md](/zh/docs/gallery/)     # 画廊
  - image/                                             # 页面包
    - [index.zh.md](/zh/docs/image/)       # 图片
- [hugo.yaml](https://github.com/pgsty/oink.pgsty.com/blob/main/hugo.yaml)   # 站点配置（GitHub）
```

## 按平台分成标签页 {#tabs}

围栏带 `tab=`（以及 `group=` `value=`）时成为一组[标签页](/zh/docs/tabs/)中的一页，可以与代码围栏混排。

````markdown {title="源码"}
```filetree {tab="Linux" group="platform" value="linux"}
- /etc/pigsty/          # 配置
- /var/lib/pgsql/       # 数据
- /usr/bin/pig          # 可执行文件
```
```filetree {tab="macOS" value="macos"}
- ~/Library/Application Support/pigsty/   # 配置
- /opt/homebrew/bin/pig                   # 可执行文件
```
````

```filetree {tab="Linux" group="platform" value="linux"}
- /etc/pigsty/          # 配置
- /var/lib/pgsql/       # 数据
- /usr/bin/pig          # 可执行文件
```
```filetree {tab="macOS" value="macos"}
- ~/Library/Application Support/pigsty/   # 配置
- /opt/homebrew/bin/pig                   # 可执行文件
```

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | `<div class="td-filetree">`，可选标题栏，目录是原生 `<details>`；带注释时多一条可拖动分隔条（唯一的运行时） |
| 打印 | 同一棵树，全部展开，没有分隔条，注释换行不截断 |
| Markdown | 原样输出 `filetree` 围栏 |
| RSS | 围栏源码放进 `<pre>` |

窄屏（小于 `sm` 断点）时布局收成单列：注释移到名称下方，不再截断，分隔条隐藏。不带注释的树是单列，也不加载任何脚本。

## 参数参考 {#reference}

围栏属性（写在 ```` ```filetree ```` 后面）：

| 属性 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `title` | 纯文本 | — | 树上方的标题栏；不写就不画；不能为空 |
| `tab` | 纯文本 | — | 让这棵树成为一个标签页 |
| `group` / `value` | 字符串 | — | 标签页分组与同步值；必须与 `tab` 同时出现 |
| `class` | class 列表 | — | 透传给站点 CSS |
{.fields meta="type default"}

条目属性（写在每行末尾的 `{…}` 里）：

| 属性 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `icon` | Font Awesome class 对 | 按名字 / 扩展名匹配 | 例如 `fa-solid fa-lock`；格式不符构建失败 |
| `tone` | 枚举 | `neutral` | `neutral` `info` `success` `warning` `danger`，只给图标上色 |
| `open` | 布尔 | `true` | 仅目录；`false` 表示初始收起 |
| `type` | 枚举 | 自动判断 | `dir` 或 `file`，覆盖自动判断 |
{.fields meta="type default"}

行语法本身：

| 元素 | 说明 |
| --- | --- |
| 缩进 | 两个空格 / 四个空格 / 制表符 / `tree` 的 `│ ├── └──` 连线都行 |
| `- name` | 项目符号可省略；`-` `*` `+` 等价 |
| `name/` | 结尾斜杠表示目录；名字原样渲染，斜杠保留 |
| `[name](url)` | 带链接的条目 |
| `# 注释` | 第一个前面带空白的 `#` 之后的内容；`\#` 是字面井号 |
| `N directories, M files` | `tree` 的统计行，自动丢弃 |
{.fields}

未知属性、未知取值、写在文件上的 `open`、格式错误的 `{…}`、退回到未打开过的缩进层级，都会构建失败，并给出围栏内的行号。

## 限制与常见问题 {#limits}

- 只有 `filetree` 围栏这一种形态：没有 `{.filetree}` 列表标记，也没有 shortcode。
- 注释与名字都是纯文本：写 `**粗体**` 会原样显示，围栏源码在任何环境里都读得通。
- 不读取磁盘：树是手写或粘贴的静态内容，不随仓库变化。
- 不提供搜索、多选、复制整棵树：需要逐字复制时用普通代码块。
- 分栏宽度不持久化：拖动过的位置刷新后回到构建期算出的默认值。

## 相关 {#related}

- [代码块](/zh/docs/code/) — 需要逐字复制的清单
- [标签页](/zh/docs/tabs/) — 按平台并列多棵树
- [徽章](/zh/docs/badge/) — `tone` 用的是同一套词汇
- [目录与页面组织](https://oink.pgsty.com/zh/docs/write/organize/) — 真实的内容目录该怎么排
