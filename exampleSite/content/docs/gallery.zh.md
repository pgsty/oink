---
title: 画廊
linkTitle: 画廊
description: 用 `gallery` 围栏把一组相关截图排成响应式网格，每张可带说明或链接，并复用页面的图片缩放对话框。
weight: 170
search_keywords: [画廊, Gallery, 图库, 截图网格, 围栏, 图片缩放, image zoom, link, class]
image_zoom: true
---

画廊（Gallery）把一组相关图片排成响应式网格，围栏里每行一张图。适用于同一件事的几个视图：几张截图、几种状态、几套配色。单张图用[图片](/zh/docs/image/)；相互之间没有顺序与对比关系的图片不适合放进同一个画廊。

## 最简例子 {#minimal}

围栏里一行一张图，语法是 Markdown 的 `![替代文字](来源)`。

````markdown {title="源码"}
```gallery
![OINK 的默认文档外壳](/images/oink.webp)
![上游 Docsy 的经典布局](/images/docsy.webp)
```
````

```gallery
![OINK 的默认文档外壳](/images/oink.webp)
![上游 Docsy 的经典布局](/images/docsy.webp)
```

替代文字必须写：它是这一项的标题、读屏器唯一能读到的文字，也决定这张图是否参与缩放。列数没有参数，网格随容器宽度自适应，窄屏减列。

## 加说明 {#description}

图片后面用 ` # ` 起头写说明，显示在图下方。说明是纯文本，里面的 Markdown 按字面显示；要一个字面井号写 `\#`。

````markdown {title="源码"}
```gallery
![OINK 文档页面的三栏布局](/images/oink.webp) # 默认外壳：侧栏、正文、目录
![Docsy 的经典文档布局](/images/docsy.webp) # OINK 的上游 Docsy，内容模型一脉相承
![发布说明页面](/images/releasenote.webp) # 发布页由 data/download 里的事实生成，不联网
```
````

```gallery
![OINK 文档页面的三栏布局](/images/oink.webp) # 默认外壳：侧栏、正文、目录
![Docsy 的经典文档布局](/images/docsy.webp) # OINK 的上游 Docsy，内容模型一脉相承
![发布说明页面](/images/releasenote.webp) # 发布页由 data/download 里的事实生成，不联网
```

说明长短可以不一致：网格按最高的一项对齐，说明换行不影响相邻的图。图片先被解析，替代文字与路径里的 `#` 不需要转义。

## 每项一个链接 {#link}

行尾的 `{link=…}` 让这一项成为链接，站内路径、相对路径、`http(s):` 都可以。

````markdown {title="源码"}
```gallery
![OINK 的默认文档外壳](/images/oink.webp) # 点击进入「图片」组件页 {link=/zh/docs/image/}
![发布说明页面](/images/releasenote.webp) # 点击进入「发布与下载」 {link=https://oink.pgsty.com/zh/docs/write/releases/}
```
````

```gallery
![OINK 的默认文档外壳](/images/oink.webp) # 点击进入「图片」组件页 {link=/zh/docs/image/}
![发布说明页面](/images/releasenote.webp) # 点击进入「发布与下载」 {link=https://oink.pgsty.com/zh/docs/write/releases/}
```

带链接的项不参与缩放，点击已有别的含义。同一个画廊里两种项可以混排：有链接的打开页面，没有链接的打开大图。

## 图片来源 {#sources}
来源解析顺序与普通图片一致：页面资源（页面包里的同目录文件）→ 全局资源 `assets/` → 静态路径 `/images/…` → 远程 URL。本站的共享演示图不需要构建期处理，因此统一放在 `static/images/`，避免为样例增加额外目录。

````markdown {title="源码"}
```gallery
![OINK 文档总览](/images/oink.webp) # 来自 static/images/…，原样发布
![OINK 发布说明](/images/releasenote.webp) # 与上一张图共用同一个简单目录
```
````

```gallery
![OINK 文档总览](/images/oink.webp) # 来自 static/images/…，原样发布
![OINK 发布说明](/images/releasenote.webp) # 与上一张图共用同一个简单目录
```

页面资源与全局资源找不到时构建失败；静态路径与远程 URL 不检查存在性。

## 装饰图与缩放 {#zoom}

替代文字留空表示这是装饰性图片：没有标题，读屏器跳过，也不参与缩放。

图片缩放是站点级开关，默认关闭。本页在 front matter 中开启了它，上面每张有替代文字、没有链接的图都可以点开看大图（<kbd>Esc</kbd> 关闭，焦点回到原处）。

```yaml {title="这一页的 front matter"}
params:
  ui:
    image_zoom:
      enable: true
```

````markdown {title="源码：一张装饰图配一张正常图"}
```gallery
![](/images/docsy.webp) # 装饰性配图，不参与缩放
![Pigsty 发布说明页面](/images/releasenote.webp) # 有替代文字，可以点开
```
````

```gallery
![](/images/docsy.webp) # 装饰性配图，不参与缩放
![Pigsty 发布说明页面](/images/releasenote.webp) # 有替代文字，可以点开
```

画廊没有自己的缩放运行时，复用整页共用的那个对话框。页面上没有可缩放的图时，运行时不加载。细节见[图片 · 缩放](/zh/docs/image/#zoom)。

## 加 class 与分标签页 {#class-and-tabs}

`class` 可以加在整个围栏上（写在语言后面）或某一项上（行尾），主题不解释它，原样透传给站点 CSS。围栏带 `tab=`（以及 `group=` `value=`）时成为一组[标签页](/zh/docs/tabs/)里的一页。

````markdown {title="源码"}
```gallery {tab="OINK" group="shell" value="oink"}
![OINK 的默认文档外壳](/images/oink.webp) # 侧栏、正文、目录
```
```gallery {tab="Docsy" value="docsy"}
![上游 Docsy 的经典布局](/images/docsy.webp) # 内容模型一脉相承
```
````

```gallery {tab="OINK" group="shell" value="oink"}
![OINK 的默认文档外壳](/images/oink.webp) # 侧栏、正文、目录
```
```gallery {tab="Docsy" value="docsy"}
![上游 Docsy 的经典布局](/images/docsy.webp) # 内容模型一脉相承
```

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | `<ul class="td-gallery">`，每项一个 `<li>`；符合条件的图带 `data-td-image-zoom` 标记；全部懒加载 |
| 打印 | 同一组图堆叠排列，没有缩放标记 |
| Markdown | 原样输出 `gallery` 围栏 |
| RSS | 与打印相同的静态堆叠 |

画廊不加载 JavaScript。

## 参数参考 {#reference}

行语法 `![alt](src) [# 说明] [{key=value …}]`：

| 元素 | 必填 | 说明 |
| --- | --- | --- |
| `![alt](src)` | 是 | 必须顶在行首。`alt` 是这一项的标题；留空表示装饰图 |
| `src` | 是 | 页面资源 / 全局资源 / 静态路径 / 远程 URL |
| `# 说明` | 否 | 纯文本，显示在图下方；`\#` 是字面井号；不能为空 |
| `{link=…}` | 否 | 让这一项成为链接，因而不可缩放 |
| `{class=…}` | 否 | 给这一项加站点 CSS class |
{.fields}

围栏属性：

| 属性 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `tab` | 纯文本 | — | 让这个画廊成为一个标签页 |
| `group` / `value` | 字符串 | — | 标签页分组与同步值；必须与 `tab` 同时出现 |
| `class` | class 列表 | — | 透传给站点 CSS |
{.fields meta="type default"}

没有 `columns`、`caption`、`title` 属性。行首不是图片、`#` 之外的尾随文字、空说明、未知属性、格式错误的 `{…}` 都会让构建失败，报错给出围栏内的行号。

## 限制与常见问题 {#limits}

- 只有围栏一种形态：没有 `{.gallery}` 列表标记，也没有 shortcode。代价是源码在 GitHub 上不渲染成图片，收益是四态输出与缩放资格由主题保证。
- 不能指定列数，也不裁成统一宽高比：网格按视口自适应，图片按原始比例排列。
- 没有幻灯片、轮播与上一张 / 下一张：缩放对话框一次显示一张。
- 不下载远程图：构建期没有网络请求，远程图在浏览器加载前尺寸未知，可能跳版。
- 说明不解析 Markdown：需要富文本时写在画廊下方的段落里。

## 相关 {#related}

- [图片](/zh/docs/image/) — 单张图、图注、编号、缩放开关
- [卡片](/zh/docs/cards/) — 带图片的链接网格
- [标签页](/zh/docs/tabs/) — 按平台 / 主题并列多组图
- [文件树](/zh/docs/filetree/) — 行语法与画廊同源
