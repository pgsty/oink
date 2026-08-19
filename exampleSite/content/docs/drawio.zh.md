---
title: Draw.io
linkTitle: Draw.io
description: 把带着可编辑副本的 `.drawio.svg` 当普通图片放进页面，读者鼠标移上去就能点开 Draw.io 编辑器改图。
icon: fa-solid fa-compass-drafting
weight: 140
search_keywords: [drawio-server, Draw.io, diagrams.net, drawio, mxfile, 可编辑图, SVG, 编辑按钮]
---

Draw.io 集成没有围栏也没有 shortcode，用的是普通 Markdown 图片。Draw.io 导出时勾上「Include a copy of my diagram」，SVG 或 PNG 里会带一份 `mxfile` 源码；主题的运行时识别这份副本后，给图片加一个编辑按钮。适合需要读者取走修改的图；只用于展示的图按普通[图片](/zh/docs/image/)处理。下面的例子只给源码，本页不自带任何图形文件。

## 最简例子 {#minimal}

写法与普通图片相同，文件名不受限制，`.drawio.svg` 只是惯例。

```markdown {title="源码"}
![Hugo 构建流水线：content 目录经 Hugo 产出 public 目录](pipeline.drawio.svg)
{width="620" height="140"}
```

导出时带上 `mxfile` 副本的图会被包进 `.drawio` 容器。鼠标移到图上时，右下角出现一个铅笔按钮；点击后在当前页面盖一层全屏 iframe，加载站点配置的编辑器。

## 副本检测 {#detection}

运行时的判断依据只有一条：文件内容里有没有 `mxfile` 字样，与文件名无关。写法完全相同的手绘 SVG —— 同样是块级图片、同样的属性行 —— 因为没有副本，也就没有按钮。

```markdown {title="源码"}
![文档外壳的三栏：侧栏、正文、目录](plain-shell.svg)
{width="620" height="140"}
```

## 带图注 {#caption}

Draw.io 图片走的是普通图片渲染钩子，[图片](/zh/docs/image/)的属性照常可用。加 `caption` 得到带图注的 figure，编辑按钮仍然出现在图上。

```markdown {title="源码"}
![Hugo 构建流水线](pipeline.drawio.svg)
{caption="内容、配置与主题模板汇进 Hugo，产出 public/ 目录" width="620" height="140"}
```

## 编号成书里的图 {#numbered}

加 `{#id num=…}` 得到一张可交叉引用的编号图，与别的图片一样能被 `xref` 引用、进入图目录。

```markdown {title="源码"}
![Hugo 构建流水线](pipeline.drawio.svg)
{#fig_pipeline num="1-1" caption="从内容到静态站点" width="620" height="140"}
```

编号与交叉引用的完整规则见[书籍出版](https://oink.pgsty.com/zh/docs/write/book/)。

## SVG 还是 PNG {#svg-or-png}

两种都识别。Draw.io 导出 PNG 时同样能带上副本，存在 PNG 的文本块里，运行时的判断逻辑相同。

```markdown {title="源码"}
![Hugo 构建流水线（PNG 导出）](pipeline.drawio.png)
{width="620" height="140"}
```

文档里优先用 SVG：缩放不失真，文字是真实文本（可被搜索、可被读屏器读取），改动的 diff 也读得懂。图特别复杂、或目标平台不支持 SVG 时用 PNG。只有 PNG 能走 Hugo 的图片处理，`command=` / `options=` 用在 SVG 上会构建失败。

## 编辑流程 {#editing}

按钮依次做三件事。

{{% steps %}}

### 盖一层遮罩 {#editing-overlay}

页面上插入一个全屏的 `div.drawioframe`，里面是一个 iframe，地址是配置的 `drawio_server` 加上一串固定参数（`embed=1&ui=atlas&proto=json&saveAndEdit=1&noSaveBtn=1`）。

### 把图送进编辑器 {#editing-load}

编辑器就绪后，运行时把这张图片的内容（含 `mxfile` 副本）作为 data URL 发进 iframe。这一步不经过你的服务器。

### 保存与回写 {#editing-save}

在编辑器里点保存，运行时让编辑器按原格式（SVG 或 PNG）导出，由浏览器下载成同名文件。运行时不写回仓库：把下载到的文件覆盖 `content/` 里那一份，再自行提交。

{{% /steps %}}

编辑按钮供读者取走图去改，不是站点的在线编辑功能。

## 编辑器地址 {#server}

```yaml {title="hugo.yaml"}
params:
  drawio:
    enable: true
    drawio_server: https://drawio.internal.example/
```

- `enable: true` 却没写 `drawio_server` → 构建报错 `params.drawio.enable requires an explicit params.drawio.drawio_server`。主题不代替站点选择公共服务。
- 编辑过程必须留在组织内部时，部署一份[自托管编辑器](https://github.com/jgraph/docker-drawio)，把地址指向它。
- 公共端点 `https://embed.diagrams.net/` 可用，读者的图会进入第三方页面。

这两个键的完整定义在[配置总览](https://oink.pgsty.com/zh/docs/customize/config/)。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | 普通 `<img>`（或 `<figure>`）；启用后运行时把带副本的图包进 `<div class="drawio">` 并加按钮 |
| 打印 | 图片照常打印；按钮默认隐藏（只在悬停时出现），打印上不会有它 |
| Markdown | 普通 Markdown 图片语法 |
| RSS | 普通 `<img>`，绝对 URL，没有按钮 |

图片本身在四态里都在，编辑按钮是增量能力。

## 参数参考 {#reference}

没有专属的围栏或 shortcode 参数。图片属性行沿用[图片](/zh/docs/image/)那一套（`caption` `width` `height` `link` `#id` `num` `command` `options`）。

站点参数（`hugo.yaml`）：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `params.drawio.enable` | bool | `false` | 关闭时不加载任何脚本，图片就是图片 |
| `params.drawio.drawio_server` | string | 无 | 编辑器地址；`enable: true` 时必填，否则构建失败 |
{.fields meta="type default"}

## 限制与常见问题 {#limits}

- 运行时进入每一个页面：站点开了 `params.drawio.enable`，脚本就无条件加载（不像别的组件按页面用量决定），并且会对页面上每一张 `.svg` / `.png` 图片各发一次 XHR 去读内容找 `mxfile`。图多的页面这是一笔实打实的开销，不常用 Draw.io 的站点不建议开启。
- 导出时忘了勾「Include a copy of my diagram」，图就只是一张图，没有按钮。
- 编辑依赖编辑器，且不写回仓库：离线环境里图片正常显示，按钮点了没有反应；编辑器保存等于浏览器下载，替换文件与提交都要手动做。
- 按钮只在悬停时出现：触屏设备上没有 hover，读者不容易发现它，不要把可编辑当成关键功能来讲。
- 配色不跟随深浅色：导出的 SVG 颜色是固定的；把填充设成 `none`、线条与文字用中性灰，两种模式下都能看。

## 相关 {#related}

- [图片](/zh/docs/image/) — 图注、编号、尺寸、缩放的完整规则
- [PlantUML](/zh/docs/plantuml/) — 另一个需要自建服务的图表集成
- [Mermaid](/zh/docs/mermaid/) — 不需要任何服务的文本画图
- [配置总览](https://oink.pgsty.com/zh/docs/customize/config/) — `params.drawio.*` 的完整定义
