---
title: 步骤
linkTitle: 步骤
description: 有序列表加 `{.steps}` 就是带编号圆点与竖线的操作步骤；步骤要带标题、要进目录时改用 steps shortcode。
icon: fa-solid fa-list-ol
weight: 70
search_keywords: [步骤, Steps, 有序列表, 操作步骤, 教程, ol, start, 目录, TOC]
---

步骤（Steps）是带编号圆点与竖线的有序列表：一个普通有序列表，加一行 `{.steps}` 标记，编号圆点与串起它们的竖线由 CSS 绘制，不加载脚本。用于有先后的操作流程。并列而无先后的内容用普通列表或卡片。

写法有两种：有序列表加 `{.steps}`（默认选它），以及 `{{%/* steps */%}}` shortcode，每一步要有自己的标题、标题还要进右侧目录时用它。

## 最简例子 {#minimal}

每一项都写 `1.`，让 Markdown 自己数。这样插入、删除、调换步骤都不用手改编号，而且内容缩进恒定是三个空格。

```markdown {title="源码"}
1. 安装 Hugo Extended
1. 克隆文档站
1. 启动本地预览
{.steps}
```

1. 安装 Hugo Extended
1. 克隆文档站
1. 启动本地预览
{.steps}

`{.steps}` 必须紧贴列表最后一行，中间空一行它就会变成正文里一段可见的花括号。

## 步骤内容 {#blocks}
列表项里可以放任何块级内容：段落、代码围栏、提示块、表格、嵌套列表、图片。缩进对齐到列表项的内容列（三个空格）即可。

````markdown {title="源码"}
1. 克隆文档站，它本身就是主题的完整示例。

   ```bash
   git clone https://github.com/pgsty/oink.pgsty.com my-docs
   cd my-docs
   ```

1. 启动本地服务器。

   ```bash
   hugo server
   ```

   > [!NOTE]
   > 首次构建会通过 Go 模块代理拉取主题，需要本机安装 Go。

1. 替换三处内容，它就是你的站点。

   | 位置 | 替换为 |
   | --- | --- |
   | `hugo.yaml` 的 `title` | 你的站名 |
   | `hugo.yaml` 的 `baseURL` | 你的域名 |
   | `content/` | 你的内容 |
{.steps}
````

1. 克隆文档站，它本身就是主题的完整示例。

   ```bash
   git clone https://github.com/pgsty/oink.pgsty.com my-docs
   cd my-docs
   ```

1. 启动本地服务器。

   ```bash
   hugo server
   ```

   > [!NOTE]
   > 首次构建会通过 Go 模块代理拉取主题，需要本机安装 Go。

1. 替换三处内容，它就是你的站点。

   | 位置 | 替换为 |
   | --- | --- |
   | `hugo.yaml` 的 `title` | 你的站名 |
   | `hugo.yaml` 的 `baseURL` | 你的域名 |
   | `content/` | 你的内容 |
{.steps}

`{{</* … */>}}` 形式的 shortcode（标签页、卡片、徽章等）也可以写在列表项里；`{{%/* … */%}}` 形式不行，见下面的[限制](#limits)。

## 一步里按平台分开 {#tabs-in-steps}

某一步在不同平台上命令不同时，把带 `{tab=}` 的围栏并排写进那个列表项，它们照样会合成标签页。

`````markdown {title="源码"}
1. 安装 Hugo Extended。

1. 安装依赖：

   ```bash {tab="EL / RHEL" group="stepdemo" value="rpm"}
   sudo dnf install golang git
   ```
   ```bash {tab="Debian / Ubuntu" value="deb"}
   sudo apt install golang-go git
   ```

1. 运行 `hugo server` 预览。
{.steps}
`````

1. 安装 Hugo Extended。

1. 安装依赖：

   ```bash {tab="EL / RHEL" group="stepdemo" value="rpm"}
   sudo dnf install golang git
   ```
   ```bash {tab="Debian / Ubuntu" value="deb"}
   sudo apt install golang-go git
   ```

1. 运行 `hugo server` 预览。
{.steps}

## 接着上一组往下编号 {#start}

正文隔断了一组步骤时，把新一组的第一项写成它实际的序号，Markdown 会输出 `start`，编号从那里继续（支持到 40）。

```markdown {title="源码"}
4. 配置 `baseURL` 与部署工作流。
1. 推送到 `main`，等待 GitHub Actions 构建完成。
{.steps}
```

4. 配置 `baseURL` 与部署工作流。
1. 推送到 `main`，等待 GitHub Actions 构建完成。
{.steps}

## 带标题的步骤 {#shortcode}

步骤本身很长、每一步该有个能被链接和被目录收录的标题时，用 `{{%/* steps */%}}`：它的正文是页面级 Markdown，里面的每一个直接子标题就是一步，正文不用缩进。下面三步的标题就在这一页的右侧目录里。

```markdown {title="源码"}
{{%/* steps */%}}

### 安装工具链 {#install-toolchain}

需要 Hugo Extended ≥ 0.160.1 与 Go。

### 启动服务器 {#run-server}

{{</* tabs group="oink-os" default="macos" */>}}
{{</* tab label="macOS" value="macos" */>}}
`brew install hugo go`
{{</* /tab */>}}
{{</* tab label="Debian" value="debian" */>}}
`sudo apt install hugo golang-go`
{{</* /tab */>}}
{{</* /tabs */>}}

### 发布 {#publish}

推送到 `main`，仓库自带的工作流会构建并发布。

{{%/* /steps */%}}
```

{{% steps %}}

### 安装工具链 {#install-toolchain}

需要 Hugo Extended ≥ 0.160.1 与 Go。

### 启动服务器 {#run-server}

{{< tabs group="oink-os" default="macos" >}}
{{< tab label="macOS" value="macos" >}}
`brew install hugo go`
{{< /tab >}}
{{< tab label="Debian" value="debian" >}}
`sudo apt install hugo golang-go`
{{< /tab >}}
{{< /tabs >}}

### 发布 {#publish}

推送到 `main`，仓库自带的工作流会构建并发布。

{{% /steps %}}

它是主题里唯一的 `{{%/* … */%}}` shortcode。百分号形式的正文交给 Goldmark 当页面级 Markdown 处理：只有这样，里面的标题才能进目录，里面才能放 `tabs`、`cards`、`fields` 这些容器 shortcode。代价是它自己不能嵌进列表项，也不能嵌进另一个百分号容器。

同一组步骤的标题保持同一层级，不要把一个 `steps` 套进另一个里。

## 两种形态的选择 {#which}
| 情况 | 用法 |
| --- | --- |
| 步骤是一两句话加一段命令 | 有序列表 + `{.steps}` |
| 每一步需要标题、需要被链接、需要进目录 | `{{%/* steps */%}}` |
| 步骤里要放 `tabs`、`cards`、`fields` 容器 | `{{%/* steps */%}}` |
| 步骤本身要嵌在另一个列表项里 | 有序列表 + `{.steps}` |

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | 原生形态是 `<ol class="steps">`，编号与竖线由 CSS 画；shortcode 形态是 `<div class="td-steps">` 加各级标题 |
| 打印 | 编号与内容照旧，竖线保留 |
| Markdown | 原样输出源码：有序列表加 `{.steps}`，或标题加正文 |
| RSS | 静态列表 / 标题分节 |

不加载脚本；关闭 JavaScript 后呈现不变。

## 参数参考 {#reference}

两种形态都没有参数，只有写法约定：

| 写法 | 位置 | 说明 |
| --- | --- | --- |
| `{.steps}` | 有序列表下一行 | 必需；写在无序列表上不生效 |
| `1.` | 每一项 | 让 Markdown 自己数；内容缩进恒为三个空格 |
| `4.`（首项） | 第一项 | 输出 `<ol start="4">`，编号从 4 接着走，支持 2–40 |
| `{{%/* steps */%}}` | 包住若干标题 | 直接子标题（`##`–`######`）就是步骤；正文不缩进 |
{.fields meta="-"}

## 限制与常见问题 {#limits}

- 列表项里不能写 `{{%/* … */%}}`：百分号 shortcode 的多行输出会把列表截断。要在步骤里放容器就整组改用 shortcode 形态。
- `{{%/* steps */%}}` 不能放进列表项，也不能套在另一个百分号容器里。
- 标记要紧贴列表：`{.steps}` 与列表之间不能有空行；经过 Prettier 之类的格式化工具时，把它包进 `<!-- prettier-ignore-start -->` / `<!-- prettier-ignore-end -->`。
- `{.steps}` 只对有序列表有效：写在 `-` 开头的无序列表上不会有编号。
- 步骤不折叠、不记进度：没有「已完成」状态，也没有展开收起。

## 相关 {#related}

- [标签页](/zh/docs/tabs/) — 按平台分开的命令
- [提示块](/zh/docs/callout/) — 某一步里的前提与警告
- [代码块](/zh/docs/code/) — 步骤里的命令
- [卡片](/zh/docs/cards/) — 步骤做完之后的「下一步」
