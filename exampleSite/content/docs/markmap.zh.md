---
title: 思维导图
linkTitle: 思维导图
description: 用 `markmap` 围栏把一段 Markdown 大纲变成可展开、可缩放的思维导图，源码本身就是能读的提纲。
icon: fa-solid fa-brain
weight: 130
search_keywords: [思维导图, Markmap, mind map, 大纲, outline, 脑图, 树状图]
---

`markmap` 围栏的正文是一段普通的 Markdown 大纲：标题与列表决定层级，浏览器把它画成一棵可展开、可折叠的树。适合把「这一节讲了什么」的层级一次呈现。节点之间有方向、有条件的流程用 [Mermaid](/zh/docs/mermaid/)。

## 最简例子 {#minimal}

````markdown {title="源码"}
```markmap
# OINK
## 本地优先
- 运行时全部随主题分发
- 不依赖任何 CDN
## Markdown 原生
- 组件是围栏和属性行
- 不写 shortcode 也能用
## 四态输出
- HTML
- 打印
- Markdown
- RSS
```
````

```markmap
# OINK
## 本地优先
- 运行时全部随主题分发
- 不依赖任何 CDN
## Markdown 原生
- 组件是围栏和属性行
- 不写 shortcode 也能用
## 四态输出
- HTML
- 打印
- Markdown
- RSS
```

一级标题是根节点，其余标题与列表项按缩进挂在它下面。点击节点上的圆点折叠或展开这一支，鼠标滚轮缩放，拖动平移。右下角一排工具按钮提供缩放、适应窗口与下载 SVG。

## 多层级 {#depth}

层级越深字号越小，画布自动排布。下面是本站文档的六个栏目与它们的页数。

````markdown {title="源码"}
```markmap
# OINK 文档
## 简介（4 页）
### 它是什么
### 功能一览
### 案例
### 许可
## 快速上手（3 页）
### Fork 本站
### 目录结构
### 从零开始
## 创作内容（8 页）
### 组织内容
### 编写页面
### 页面参数
### 博客
### 书籍
### 发布与下载
### OpenAPI
## 组件（22 页）
### 提示块 / 标签页 / 步骤 / 卡片
### 图片 / 画廊 / 表格 / 参数表
### 图表：Mermaid / PlantUML / 思维导图 / ECharts
## 定制站点（15 页）
### 品牌 / 导航 / 搜索 / 多语言
### 首页 / 版本 / 分类 / 打印
## 维护管理（7 页）
### 预览 / 部署 / 升级
### 评论 / 统计 / 排错
```
````

```markmap
# OINK 文档
## 简介（4 页）
### 它是什么
### 功能一览
### 案例
### 许可
## 快速上手（3 页）
### Fork 本站
### 目录结构
### 从零开始
## 创作内容（8 页）
### 组织内容
### 编写页面
### 页面参数
### 博客
### 书籍
### 发布与下载
### OpenAPI
## 组件（22 页）
### 提示块 / 标签页 / 步骤 / 卡片
### 图片 / 画廊 / 表格 / 参数表
### 图表：Mermaid / PlantUML / 思维导图 / ECharts
## 定制站点（15 页）
### 品牌 / 导航 / 搜索 / 多语言
### 首页 / 版本 / 分类 / 打印
## 维护管理（7 页）
### 预览 / 部署 / 升级
### 评论 / 统计 / 排错
```

## 链接、代码与强调 {#inline-markdown}

节点里可以写行内 Markdown：链接可点击，行内代码用等宽字体，粗体与斜体照常生效。

````markdown {title="源码"}
```markmap
# 日常命令
## 预览
- `hugo server` — 打开 [localhost:1313](http://localhost:1313/)
- `hugo server -D` — **连草稿一起**预览
## 构建
- `hugo --printPathWarnings --panicOnWarning`
- `hugo --gc --minify` — 发布用
## 主题
- `hugo mod get -u github.com/pgsty/oink`
- [主题仓库](https://github.com/pgsty/oink)
- [本站源码](https://github.com/pgsty/oink.pgsty.com)
```
````

```markmap
# 日常命令
## 预览
- `hugo server` — 打开 [localhost:1313](http://localhost:1313/)
- `hugo server -D` — **连草稿一起**预览
## 构建
- `hugo --printPathWarnings --panicOnWarning`
- `hugo --gc --minify` — 发布用
## 主题
- `hugo mod get -u github.com/pgsty/oink`
- [主题仓库](https://github.com/pgsty/oink)
- [本站源码](https://github.com/pgsty/oink.pgsty.com)
```

## 节点里的公式 {#math}

Markmap 运行时带了一份本地 KaTeX，节点里的 `$…$` 会被渲染成公式。

````markdown {title="源码"}
```markmap
# 常看的几个 PostgreSQL 指标
## 缓存命中率
- $\frac{blks\_hit}{blks\_hit + blks\_read}$
- 低于 0.99 时检查 shared_buffers
## 复制延迟
- $lsn_{primary} - lsn_{replica}$
## 事务吞吐
- $TPS = \frac{\Delta xact\_commit}{\Delta t}$
```
````

```markmap
# 常看的几个 PostgreSQL 指标
## 缓存命中率
- $\frac{blks\_hit}{blks\_hit + blks\_read}$
- 低于 0.99 时检查 shared_buffers
## 复制延迟
- $lsn_{primary} - lsn_{replica}$
## 事务吞吐
- $TPS = \frac{\Delta xact\_commit}{\Delta t}$
```

## 控制初始展开层数 {#options}

围栏正文最前面可以写一段 Markmap 自己的 YAML 头，它不是 Hugo front matter。`initialExpandLevel` 只展开前几层，其余分支由读者点开。`colorFreezeLevel` 指定从第几层起同一分支使用同一种颜色。

````markdown {title="源码"}
```markmap
---
markmap:
  initialExpandLevel: 2
  colorFreezeLevel: 2
---

# 主题仓库的检查脚本
## 源码级契约
### check-i18n.py
### check-taxonomy.py
### check-font-tokens.py
## 输出级检查
### check-output.py
### check-goldens.py
### check-code-blocks.py
### check-content-primitives.py
### check-media-primitives.py
## 浏览器运行时
### node --test tests/js/**/*.test.js
```
````

```markmap
---
markmap:
  initialExpandLevel: 2
  colorFreezeLevel: 2
---

# 主题仓库的检查脚本
## 源码级契约
### check-i18n.py
### check-taxonomy.py
### check-font-tokens.py
## 输出级检查
### check-output.py
### check-goldens.py
### check-code-blocks.py
### check-content-primitives.py
### check-media-primitives.py
## 浏览器运行时
### node --test tests/js/**/*.test.js
```

## 折进折叠块 {#in-details}

每张导图固定 300 像素高，正文里连着放三张会占掉大量版面。把全景图折进 `> [!DETAILS]`，由读者自己展开。折叠块里的每一行都要以 `>` 开头，围栏也不例外。

````markdown {title="源码"}
> [!DETAILS] 主题仓库长什么样
> ```markmap
> # pgsty/oink
> ## layouts/
> - baseof.html 与各类型的壳
> - _partials/shell/
> - _markup/ 渲染钩子
> - _shortcodes/
> ## assets/
> - scss/ 令牌与组件样式
> - js/ 浏览器运行时
> - third_party/ 随主题分发的库
> ## i18n/
> - 32 个语言文件，键完全对齐
> ## docs/
> - 冻结契约文档
> ```
````

> [!DETAILS] 主题仓库长什么样
> ```markmap
> # pgsty/oink
> ## layouts/
> - baseof.html 与各类型的壳
> - _partials/shell/
> - _markup/ 渲染钩子
> - _shortcodes/
> ## assets/
> - scss/ 令牌与组件样式
> - js/ 浏览器运行时
> - third_party/ 随主题分发的库
> ## i18n/
> - 32 个语言文件，键完全对齐
> ## docs/
> - 冻结契约文档
> ```

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | 先输出 `<pre><code class="language-markmap">`，运行时把它换成 `<div class="markmap">` 并画出 SVG |
| 打印 | 与 HTML 相同：打印视图同样加载运行时 |
| Markdown | 原样保留 `markmap` 围栏与它的大纲源码 |
| RSS | 只有大纲源码，订阅端看到的是一段可读的提纲 |

大纲本身就是内容：拿不到 JavaScript 的地方读到的仍是完整层级。

## 参数参考 {#reference}

围栏属性：没有。`markmap` 围栏不读属性行，高度由主题固定为 300px（`.markmap > svg`），宽度撑满正文栏。

站点参数（`hugo.yaml`）：

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `params.markmap` | bool | `false` | 关闭时围栏保持为代码块，不加载任何运行时 |
{.fields meta="type default"}

键的完整定义见[配置总览](https://oink.pgsty.com/zh/docs/customize/config/)。每张图的行为写在围栏正文最前面的 `markmap:` YAML 头里（`initialExpandLevel`、`colorFreezeLevel`、`maxWidth` 等），属于 Markmap 语法，可用键以 [Markmap 文档](https://markmap.js.org/docs/json-options)为准。

## 限制与常见问题 {#limits}

- 输出是固定 300px 高的内联 SVG：高度由一条 `.markmap > svg` 规则统一，围栏改不了，层级太多时用 `initialExpandLevel` 收起或拆成两张图；内联 SVG 也不适用 `{#id num=}` 编号与图片缩放。
- 不跟随深浅色：连线颜色由 Markmap 自己的调色板决定，两种模式下都需要检查对比度。
- 没开 `params.markmap` 就只是代码块：不用这个组件的站点不加载任何运行时。
- 右下角工具栏里的「下载 SVG」是浏览器行为，导出的是当前展开状态的快照。
- 大纲里避开 `<`、`>`、`&`、`"`：当前主题版本的 `markmap` 围栏会把这几个字符二次转义，节点上会出现 `&gt;`、`&#34;` 这样的字面文本；写链接用 `[文字](URL)`，不要用尖括号自动链接。

## 相关 {#related}

- [Mermaid](/zh/docs/mermaid/) — 有方向、有条件的图
- [文件树](/zh/docs/filetree/) — 目录结构用它更准确
- [提示块](/zh/docs/callout/) — `[!DETAILS]` 折叠块的完整用法
- [配置总览](https://oink.pgsty.com/zh/docs/customize/config/) — `params.markmap`
