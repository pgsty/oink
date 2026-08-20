---
title: 标签页
linkTitle: 标签页
description: 给相邻的围栏或表格加一个 `{tab=}` 属性就得到标签页；加上 group 之后可分享链接、跨组同步、记住读者的选择。
icon: fa-solid fa-window-restore
weight: 40
search_keywords: [标签页, Tabs, tab, group, value, 同步, 持久化, localStorage, hash, 选项卡]
---

标签页并列等价的几种写法：包管理器、发行版、YAML / TOML / JSON、环境变量与配置项。有先后的步骤、互不相关的内容不适合标签页，读者一次只看见其中一个。

原生形态是给相邻的块加 `tab` 属性。正文（多个段落、列表、提示块）要做成标签页时才用 `tabs`/`tab` shortcode。两种形态共用一个运行时、一套 DOM 与一样的键盘行为。

## 最简例子 {#minimal}

连着写两个带 `tab` 的围栏，中间只隔空行。

````markdown {title="源码"}
```bash {tab="Homebrew"}
brew install hugo
```
```bash {tab="Debian / Ubuntu"}
sudo apt install hugo
```
````

```bash {tab="Homebrew"}
brew install hugo
```
```bash {tab="Debian / Ubuntu"}
sudo apt install hugo
```

服务器输出两个带标题的代码块，没有面板被隐藏；页面加载后运行时把相邻的同类块重组为标签页。在 GitHub 上、打印时、关闭 JavaScript 时，读者看到的是连续两块完整内容。

## 分组：链接、同步与记忆 {#group}

只在第一个块上写 `group`，这一组就有了公开的 URL hash `#<group>-<value>`、页内同步与浏览器持久化；分组内的每个块都要写 `value`。

````markdown {title="源码"}
```bash {tab="npm" group="pkgmgr" value="npm"}
npm create hugo-site@latest
```
```bash {tab="pnpm" value="pnpm"}
pnpm create hugo-site
```
```bash {tab="Yarn" value="yarn"}
yarn create hugo-site
```
````

```bash {tab="npm" group="pkgmgr" value="npm"}
npm create hugo-site@latest
```
```bash {tab="pnpm" value="pnpm"}
pnpm create hugo-site
```
```bash {tab="Yarn" value="yarn"}
yarn create hugo-site
```

`value` 是机器值（`^[a-z0-9][a-z0-9_-]*$`），`tab` 是给人看的标签名，两者互不相干。上面这组的 pnpm 面板对应的 hash 是 `#pkgmgr-pnpm`，带这个 hash 访问本页会直接选中它。

## 同组联动 {#sync}
下面这组用了同一个 `group="pkgmgr"`。在上面那组切换包管理器，这组会跟着切；在这组切换，上面那组也跟着切。选择写入 `localStorage` 的 `td-tabs:v1:pkgmgr` 键，在其它页面同组的标签页上仍然生效。

````markdown {title="源码"}
```bash {tab="npm" group="pkgmgr" value="npm"}
npm run build
```
```bash {tab="pnpm" value="pnpm"}
pnpm build
```
````

```bash {tab="npm" group="pkgmgr" value="npm"}
npm run build
```
```bash {tab="pnpm" value="pnpm"}
pnpm build
```

这组没有 `yarn` 面板。同步时缺哪个值就保持不动，不会出现「一组没有选中项」的状态。初始选哪个的优先级是：URL hash，存储的值，shortcode 的 `default` 或第一个块，第一个标签。带 hash 打开页面只切换，不覆盖读者已经存下的偏好。

## 表格也能做标签页 {#tables}

同一套属性写在表格的属性行上，连着的表格就组成一组标签页。

```markdown {title="源码"}
| 参数 | 默认值 |
| --- | --- |
| `shared_buffers` | 25% RAM |
| `max_connections` | 100 |
{tab="PostgreSQL 18" group="pgver" value="pg18"}

| 参数 | 默认值 |
| --- | --- |
| `shared_buffers` | 128MB |
| `max_connections` | 100 |
{tab="PostgreSQL 13" value="pg13"}
```

| 参数 | 默认值 |
| --- | --- |
| `shared_buffers` | 25% RAM |
| `max_connections` | 100 |
{tab="PostgreSQL 18" group="pgver" value="pg18"}

| 参数 | 默认值 |
| --- | --- |
| `shared_buffers` | 128MB |
| `max_connections` | 100 |
{tab="PostgreSQL 13" value="pg13"}

围栏与表格是两种块类型，相邻也不会合成同一组：一组标签页里只能全是围栏或全是表格。两者混排使用下面的 shortcode 形态。

## 标签名与文件名共存 {#tab-with-title}

围栏的 `tab` 和 `title` 可以一起写：标签名进标签栏，文件名标题栏留在面板里。

````markdown {title="源码"}
```yaml {tab="YAML" title="hugo.yaml" group="conffmt" value="yaml"}
params:
  ui:
    sidebar_menu_foldable: true
```
```toml {tab="TOML" title="hugo.toml" value="toml"}
[params.ui]
sidebar_menu_foldable = true
```
````

```yaml {tab="YAML" title="hugo.yaml" group="conffmt" value="yaml"}
params:
  ui:
    sidebar_menu_foldable: true
```
```toml {tab="TOML" title="hugo.toml" value="toml"}
[params.ui]
sidebar_menu_foldable = true
```

## 单独一个块只是带标题的块 {#single-block}

一个块要凑够两个相邻的同类块才会变成标签页。落单的块保留标题，不会变成只有一个标签的标签栏。

````markdown {title="源码"}
```ini {tab="只有这一块"}
listen_addresses = '*'
```
````

```ini {tab="只有这一块"}
listen_addresses = '*'
```

块之间只允许空行。三种情况会断开一组：中间隔了正文（段落、标题、列表都算）；中间有一条 HTML 注释，`<!-- prettier-ignore-end -->` 是常见的一处；后一个块自己写了 `group`，一组里只有第一个块可以带 `group`。

## 正文标签页 {#shortcode}

面板里要放段落、列表、提示块或多个块时，用 `tabs`/`tab` shortcode。正文是完整的 Markdown。

`````markdown {title="源码"}
{{</* tabs group="deploy" default="pages" label="部署方式" */>}}
{{</* tab label="GitHub Pages" value="pages" */>}}
仓库自带 `.github/workflows/`，推到 `main` 就会构建并发布。

> [!NOTE]
> `baseURL` 要写成仓库的 Pages 地址。
{{</* /tab */>}}
{{</* tab label="Cloudflare Pages" value="cloudflare" */>}}
在 Cloudflare 控制台里连接仓库，构建命令：

```bash
hugo --gc --minify
```
{{</* /tab */>}}
{{</* /tabs */>}}
`````

{{< tabs group="deploy" default="pages" label="部署方式" >}}
{{< tab label="GitHub Pages" value="pages" >}}
仓库自带 `.github/workflows/`，推到 `main` 就会构建并发布。

> [!NOTE]
> `baseURL` 要写成仓库的 Pages 地址。
{{< /tab >}}
{{< tab label="Cloudflare Pages" value="cloudflare" >}}
在 Cloudflare 控制台里连接仓库，构建命令：

```bash
hugo --gc --minify
```
{{< /tab >}}
{{< /tabs >}}

`default` 指定初始选中的面板，它必须是某个子项的 `value`，并且需要 `group`。没有 `group` 时不能写 `value`，主题自动生成 `tab1`、`tab2` 等值，这组标签页只在本地切换，不动 URL 也不写存储。shortcode 形态比属性形态严格：写错的地方在构建期就报出来，不留到浏览器里。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | `<div class="td-tabs">` + `role="tablist"` 的按钮与面板；运行时接管前所有面板都可见 |
| 打印 | 连续的带标题静态分节，没有标签栏 |
| Markdown | 围栏形态保持源码围栏（含 `{tab=}` 属性）；shortcode 形态输出 `**标签名**` 加正文 |
| RSS | 与打印相同，堆叠的带标题分节 |

只有用到标签页的页面才加载 `tabs.js`；打印、Markdown 与 RSS 输出不加载。

## 参数参考 {#reference}

写在围栏信息行或表格属性行上的属性：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `tab` | 非空字符串 | 无 | 可见标签名；单独出现时就是这个块的标题 |
| `group` | `^[a-z][a-z0-9_-]*$` | 无 | 写在一组的第一个块上，启用 hash、页内同步与持久化；需要 `tab` |
| `value` | `^[a-z0-9][a-z0-9_-]*$` | 无 | 分组内每个块必填，无分组时禁止；需要 `tab` |
{.fields meta="type default"}

`tabs` shortcode：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `group` | `^[a-z][a-z0-9_-]*$` | 无 | 同上，启用 hash、同步与持久化 |
| `default` | 某个子项的 `value` | 第一个子项 | 初始选中的面板；需要 `group` |
| `label` | 纯文本 | 本地化的「选项卡」 | 标签栏的无障碍名称，不显示在页面上 |
{.fields meta="type default"}

`tab` shortcode：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `label` | 纯文本 | 是 | 可见标签名 |
| `value` | `^[a-z0-9][a-z0-9_-]*$` | 有 `group` 时 | 无分组时禁止书写，自动生成 `tab1`、`tab2` 等值 |
{.fields meta="type required"}

行为约定：面板 ID 在分组里是 `<group>-<value>`，同一页出现第二组同名 `group` 时后续各组的 ID 加 `-2`、`-3` 后缀（深链目标始终是第一组），未分组时由主题生成；存储键是 `td-tabs:v1:<group>`；用户点击或按键会用 `replaceState` 更新 hash 并写入存储，带 hash 访问只切换不写入。键盘上左右方向键（感知 RTL）与 Home/End 移动并激活标签，焦点停留在标签上。

## 限制与常见问题 {#limits}

- 构建失败的写法：属性形态里 `value` 缺 `group`、`group` 或 `value` 缺 `tab`、`tab` 与编号属性 `num` 同时出现；shortcode 形态里一组内 `value` 重复、`tabs` 没有 `tab` 子项、子项之间夹着正文、`default` 不匹配任何子项的 `value`。
- 属性形态的分组错误不中断构建，只在浏览器控制台留警告：分组内漏写 `value` 时整组丢掉 `group`，退化成只在本地切换的标签页，hash、同步与持久化都没有；`value` 重复时整组跳过，那几个块保持为各自带标题的块。
- 围栏与表格不会混成一组，正文与代码混排请用 shortcode 形态。
- 标签页不是折叠块。只想收起长输出用 `> [!DETAILS]`（见[提示块](/zh/docs/callout/)）。
- 同名 `group` 是全站共享的：读者在 A 页选了 pnpm，B 页同组的标签页也会是 pnpm。这是它的用途，也意味着 `group` 名要按含义取，不用 `tabs1` 这种。

## 相关 {#related}

- [代码块](/zh/docs/code/) — 围栏的其余属性（标题、复制、行号、折叠）
- [表格](/zh/docs/table/) — 表格属性行的其余取值
- [提示块](/zh/docs/callout/) — 折叠而不是并列时用它
- [步骤](/zh/docs/steps/) — 步骤里可以放标签页
