---
title: 徽章
linkTitle: 徽章
description: 在功能名、版本号或表格单元格旁边放一枚语义状态标签，五种 tone，不需要自定义颜色。
icon: fa-solid fa-tag
weight: 180
search_keywords: [徽章, Badge, 状态标签, tone, Beta, 已弃用, neutral, info, success, warning, danger]
---

徽章（Badge）是紧跟在名字旁边的行内状态标签：Beta、已弃用、v0.5、需自建服务。适用于一两个词能说完的状态；作者只选语义 tone，颜色由主题决定，浅色与深色模式下的对比度都有保证。状态需要解释、操作步骤或截止日期时，改用正文或[提示块](/zh/docs/callout/)。

## 最简例子 {#minimal}

```markdown {title="源码"}
{{</* badge text="Beta" tone="warning" */>}}
```

{{< badge text="Beta" tone="warning" >}}

`text` 是唯一必填参数，必须是非空字符串。

## 五种 tone {#tones}

只有这五个取值，没有自定义颜色。

```markdown {title="源码"}
{{</* badge text="默认" */>}}
{{</* badge text="信息" tone="info" */>}}
{{</* badge text="已支持" tone="success" */>}}
{{</* badge text="实验性" tone="warning" */>}}
{{</* badge text="已弃用" tone="danger" */>}}
```

{{< badge text="默认" >}}
{{< badge text="信息" tone="info" >}}
{{< badge text="已支持" tone="success" >}}
{{< badge text="实验性" tone="warning" >}}
{{< badge text="已弃用" tone="danger" >}}

不写 `tone` 时使用 `neutral`。其它取值让构建失败，报错给出源文件位置。

## 夹在句子里 {#inline}

徽章是行内元素，跟在名字后面，不占单独一行。

```markdown {title="源码"}
`params.ui.image_zoom` {{</* badge text="默认关闭" tone="neutral" */>}} 打开后，
有替代文字的块级图片可以点开看大图。PlantUML {{</* badge text="需自建服务" tone="warning" */>}}
与 Draw.io {{</* badge text="需自建服务" tone="warning" */>}} 没有配置服务端点时会让构建失败，
而不是连接公共服务。
```

`params.ui.image_zoom` {{< badge text="默认关闭" tone="neutral" >}} 打开后，
有替代文字的块级图片可以点开看大图。PlantUML {{< badge text="需自建服务" tone="warning" >}}
与 Draw.io {{< badge text="需自建服务" tone="warning" >}} 没有配置服务端点时会让构建失败，
而不是连接公共服务。

## 标题旁边 {#in-headings}

**标题里不要写 shortcode。**
Hugo 先生成目录、后替换 shortcode，所以徽章在标题上渲染正常，目录里却会留下一段
Hugo 的内部占位符文本。把状态写进标题下面的第一段：

```markdown {title="源码"}
### OpenAPI 页面 {#openapi-example}

{{</* badge text="0.5 新增" tone="success" */>}} 这一节介绍……
```

### OpenAPI 页面 {#openapi-example}

{{< badge text="0.5 新增" tone="success" >}} 徽章紧跟在标题下方，目录保持干净，
锚点链接分享出去也不会带上徽章文字。

## 表格单元格里 {#in-tables}

对照表里用徽章标状态，比整列写「是」「否」更容易扫读。

```markdown {title="源码"}
| 组件 | 形态 | 状态 |
| --- | --- | --- |
| 提示块 | `> [!NOTE]` | {{</* badge text="稳定" tone="success" */>}} |
| 画廊 | ` ```gallery ` 围栏 | {{</* badge text="稳定" tone="success" */>}} |
| PlantUML | ` ```plantuml ` 围栏 | {{</* badge text="需自建服务" tone="warning" */>}} |
| `image` shortcode | — | {{</* badge text="已移除" tone="danger" */>}} |
```

| 组件 | 形态 | 状态 |
| --- | --- | --- |
| 提示块 | `> [!NOTE]` | {{< badge text="稳定" tone="success" >}} |
| 画廊 | ` ```gallery ` 围栏 | {{< badge text="稳定" tone="success" >}} |
| PlantUML | ` ```plantuml ` 围栏 | {{< badge text="需自建服务" tone="warning" >}} |
| `image` shortcode | — | {{< badge text="已移除" tone="danger" >}} |

## 列表与步骤里 {#in-lists}

```markdown {title="源码"}
1. 安装 Hugo Extended {{</* badge text="≥ 0.160.1" tone="info" */>}}
1. 克隆文档站，修改 `hugo.yaml` 里的 `baseURL`
1. `hugo server` 预览 {{</* badge text="1313 端口" tone="neutral" */>}}
{.steps}
```

1. 安装 Hugo Extended {{< badge text="≥ 0.160.1" tone="info" >}}
1. 克隆文档站，修改 `hugo.yaml` 里的 `baseURL`
1. `hugo server` 预览 {{< badge text="1313 端口" tone="neutral" >}}
{.steps}

## 卡片里 {#in-cards}

卡片有自己的 `badge` 参数（纯文本，固定在标题右侧）；卡片正文里可以放徽章 shortcode。

```markdown {title="源码"}
{{</* cards */>}}
{{</* card title="Hugo Module" icon="fa-brands fa-golang" badge="推荐" */>}}
一行 `hugo mod get` 完成安装 {{</* badge text="需要 Go" tone="info" */>}}
{{</* /card */>}}
{{</* card title="离线归档" icon="fa-solid fa-box-archive" */>}}
不联网的机器也能构建 {{</* badge text="手动升级" tone="warning" */>}}
{{</* /card */>}}
{{</* /cards */>}}
```

{{< cards >}}
{{< card title="Hugo Module" icon="fa-brands fa-golang" badge="推荐" >}}
一行 `hugo mod get` 完成安装 {{< badge text="需要 Go" tone="info" >}}
{{< /card >}}
{{< card title="离线归档" icon="fa-solid fa-box-archive" >}}
不联网的机器也能构建 {{< badge text="手动升级" tone="warning" >}}
{{< /card >}}
{{< /cards >}}

## 可点击的徽章 {#link}

加 `link` 后徽章变成链接（`<a>`），站内路径、相对路径、`http(s):`、`mailto:` 都可以。

```markdown {title="源码"}
当前版本 {{</* badge text="v0.5" tone="info" link="/zh/blog/" */>}}，
升级步骤见 {{</* badge text="版本升级" tone="neutral" link="https://oink.pgsty.com/zh/docs/admin/upgrade/" */>}}。
```

当前版本 {{< badge text="v0.5" tone="info" link="/zh/blog/" >}}，
升级步骤见 {{< badge text="版本升级" tone="neutral" link="https://oink.pgsty.com/zh/docs/admin/upgrade/" >}}。

链接非法（协议不在白名单里）会让构建失败。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | 无链接时 `<span class="td-badge td-badge--<tone>">`，有链接时 `<a class="td-badge …">` |
| 打印 | 同 HTML，静态行内元素 |
| Markdown | `**Beta**`，有链接时 `[**Beta**](/…)` |
| RSS | 同打印 |

不加载 JavaScript。徽章不是实时状态区域，新增徽章不会触发读屏器播报。

## 参数参考 {#reference}

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `text` | 纯文本 | — | 必填，非空。读者看到的文字 |
| `tone` | 枚举 | `neutral` | `neutral` `info` `success` `warning` `danger` |
| `link` | URL | — | 设置后徽章变成链接 |
{.fields meta="type default"}

只接受命名参数。没有 `icon`、`class`、`color`、`outline`、`size` 参数；写了未知参数、空 `text`、非法 `tone` 或非法链接都会让构建失败。

## 限制与常见问题 {#limits}

- 颜色不是唯一的含义载体：tone 是补充，文字要自己说清楚。`{{</* badge text="🔴" */>}}` 对读屏器没有信息。
- 没有图标参数：需要图标时改用[卡片](/zh/docs/cards/)或[提示块](/zh/docs/callout/)。
- 文字要短：徽章不换行地跟在名字后面，超过五六个字的内容写进正文。
- 同一处不超过三枚：连排的徽章会盖过它修饰的名字。
- 徽章只有 shortcode 一种形态，没有原生 Markdown 写法；纯 Markdown 阅读器里它退化成加粗文字。

## 相关 {#related}

- [卡片](/zh/docs/cards/) — `card` 自己的 `badge` 参数
- [文件树](/zh/docs/filetree/) — `tone` 用的是同一套词汇
- [按键](/zh/docs/kbd/) — 另一枚行内 shortcode
- [提示块](/zh/docs/callout/) — 状态需要解释时用它
