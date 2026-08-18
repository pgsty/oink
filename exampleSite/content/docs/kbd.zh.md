---
title: 按键
linkTitle: 按键
description: 用 `kbd` 写快捷键：一个 shortcode 接一串按键名，输出语义化的按键序列，打印与 Markdown 输出里同样可读。
weight: 190
search_keywords: [按键, Kbd, 快捷键, 键盘, shortcut, keyboard, Ctrl, Cmd, 组合键]
---

按键（Kbd）把读者要按下的键与正文区分开。适用于快捷键与组合键：一个按键一个位置参数，主题负责画框、补分隔符，并给读屏器一个可读的序列。命令名、选项名与要输入的文本用行内代码，它们不是物理按键。

## 最简例子 {#minimal}

```markdown {title="源码"}
按 {{</* kbd "Ctrl" "K" */>}} 打开命令面板。
```

按 {{< kbd "Ctrl" "K" >}} 打开命令面板。

参数必须加引号，一个按键一个参数。少于一个按键、空字符串、命名参数都会让构建失败。

## 单个按键 {#single}

一个参数对应一个键，符号键按原样写。

```markdown {title="源码"}
{{</* kbd "Escape" */>}} 关闭对话框；
{{</* kbd "/" */>}} 进入搜索；
{{</* kbd "t" */>}} 切换亮色 / 暗色；
{{</* kbd "l" */>}} 循环切换语言。
```

{{< kbd "Escape" >}} 关闭对话框；
{{< kbd "/" >}} 进入搜索；
{{< kbd "t" >}} 切换亮色 / 暗色；
{{< kbd "l" >}} 循环切换语言。

## 组合键 {#combo}

多个参数按顺序渲染，中间补 `+`。这个加号对辅助技术隐藏，读屏器读到的是本地化的连接词。

```markdown {title="源码"}
{{</* kbd "⌘" "Shift" "P" */>}} 与 {{</* kbd "Ctrl" "Shift" "P" */>}} 是同一个动作。
需要按字面的加号时，把它当成独立的一个按键：{{</* kbd "Ctrl" "+" */>}} 放大页面。
```

{{< kbd "⌘" "Shift" "P" >}} 与 {{< kbd "Ctrl" "Shift" "P" >}} 是同一个动作。
需要按字面的加号时，把它当成独立的一个按键：{{< kbd "Ctrl" "+" >}} 放大页面。

## 平台差异 {#platforms}

按键名写读者键盘上印的标签：macOS 写 `⌘`，Windows / Linux 写 `Ctrl`。不要把两个平台合进同一个序列，`Ctrl/⌘` 这类写法读屏器无法正确朗读。在句子里说明平台，或分成[标签页](/zh/docs/tabs/)。

```markdown {title="源码"}
macOS 按 {{</* kbd "⌘" "K" */>}}，Windows 与 Linux 按 {{</* kbd "Ctrl" "K" */>}}。
```

macOS 按 {{< kbd "⌘" "K" >}}，Windows 与 Linux 按 {{< kbd "Ctrl" "K" >}}。

## 快捷键表 {#in-tables}

速查表是按键最常见的位置。下面是本站生效的一部分全局键：

```markdown {title="源码"}
| 按键 | 作用 |
| --- | --- |
| {{</* kbd "Ctrl" "K" */>}} | 打开命令面板（macOS 是 {{</* kbd "⌘" "K" */>}}） |
| {{</* kbd "/" */>}} | 面板的完整搜索态 |
| {{</* kbd "t" */>}} | 切换亮色 / 暗色 |
| {{</* kbd "q" */>}} / {{</* kbd "e" */>}} | 上一篇 / 下一篇 |
| {{</* kbd "w" */>}} {{</* kbd "s" */>}} {{</* kbd "a" */>}} {{</* kbd "d" */>}} | 在侧栏树里上下移动、折叠、展开 |
| {{</* kbd "Escape" */>}} | 从侧栏树回到正文 |
```

| 按键 | 作用 |
| --- | --- |
| {{< kbd "Ctrl" "K" >}} | 打开命令面板（macOS 是 {{< kbd "⌘" "K" >}}） |
| {{< kbd "/" >}} | 面板的完整搜索态 |
| {{< kbd "t" >}} | 切换亮色 / 暗色 |
| {{< kbd "q" >}} / {{< kbd "e" >}} | 上一篇 / 下一篇 |
| {{< kbd "w" >}} {{< kbd "s" >}} {{< kbd "a" >}} {{< kbd "d" >}} | 在侧栏树里上下移动、折叠、展开 |
| {{< kbd "Escape" >}} | 从侧栏树回到正文 |

全站快捷键的完整清单见[键盘导航](https://oink.pgsty.com/zh/docs/customize/keyboard/)。

## 步骤里 {#in-steps}

```markdown {title="源码"}
1. 按 {{</* kbd "Ctrl" "K" */>}} 打开命令面板
1. 输入 `>` 进入纯命令态，或输入关键词搜索
1. 用 {{</* kbd "↑" */>}} {{</* kbd "↓" */>}} 选中一项，{{</* kbd "Enter" */>}} 前往
1. {{</* kbd "Escape" */>}} 关闭，焦点回到按下之前的位置
{.steps}
```

1. 按 {{< kbd "Ctrl" "K" >}} 打开命令面板
1. 输入 `>` 进入纯命令态，或输入关键词搜索
1. 用 {{< kbd "↑" >}} {{< kbd "↓" >}} 选中一项，{{< kbd "Enter" >}} 前往
1. {{< kbd "Escape" >}} 关闭，焦点回到按下之前的位置
{.steps}

## 原始 `<kbd>` 标签 {#raw-kbd}

Markdown 里写原始的 `<kbd>` 标签得到同样的样式，GitHub 也这么渲染。区别是分隔符与无障碍序列要自己维护：单个键两种写法都可以，组合键用 shortcode。

```markdown {title="源码"}
按 <kbd>F5</kbd> 刷新；在编辑器里按 <kbd>Ctrl</kbd>+<kbd>S</kbd> 保存。
```

按 <kbd>F5</kbd> 刷新；在编辑器里按 <kbd>Ctrl</kbd>+<kbd>S</kbd> 保存。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | `<span class="td-kbd-sequence">` 包着每个键一个 `<kbd>`；可见的 `+` 对读屏器隐藏，另有一个本地化连接词 |
| 打印 | 同 HTML，静态 |
| Markdown | 纯文本 `Ctrl + K`、`⌘ + Shift + P` |
| RSS | 同打印 |

没有 CSS 与 JavaScript 时，操作说明仍然可读。

## 参数参考 {#reference}

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| 位置参数 1..n | 字符串 | — | 至少一个，每个都必须非空且加引号；顺序就是显示顺序 |
{.fields meta="type default"}

只接受位置参数。没有 `separator`、`label`、`platform`、`class`、`size` 这些命名参数：Hugo 的 shortcode 不允许在一次调用里混用位置参数与命名参数。

## 限制与常见问题 {#limits}

- 一个序列表示同时按下的一组键：先按 A 再按 B 这类连续操作写成两个 kbd 加一句说明（先按 {{< kbd "Escape" >}}，再按 {{< kbd "Enter" >}}）。
- 不做平台检测：页面不会按访客的操作系统把 `Ctrl` 换成 `⌘`。
- 不做按键映射与录制：菜单路径、手势、游戏杆不在范围内。
- 漏写引号会让构建失败：`{{</* kbd Ctrl K */>}}` 里的 `Ctrl` 不是字符串参数。
- 不用它标命令：`hugo server` 写成行内代码，`Ctrl` 是按键。

## 相关 {#related}

- [键盘导航](https://oink.pgsty.com/zh/docs/customize/keyboard/) — 全站快捷键清单与开关
- [命令面板](https://oink.pgsty.com/zh/docs/customize/panel/) — {{< kbd "Ctrl" "K" >}} 打开的面板
- [徽章](/zh/docs/badge/) — 另一枚行内 shortcode
- [步骤](/zh/docs/steps/) — 操作说明的容器
