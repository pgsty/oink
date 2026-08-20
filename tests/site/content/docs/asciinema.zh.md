---
title: Asciinema
linkTitle: Asciinema
description: 把 .cast 终端录像放进页面：文字仍然是可选中的文字，播放器随主题分发，不连 CDN。
icon: fa-solid fa-terminal
weight: 210
search_keywords: [Asciinema, 终端录像, cast, asciicast, 录屏, 演示, terminal recording, 播放器]
---

`asciinema` 把一段 `.cast` 录像渲染成页面里的终端播放器。适用于命令行流程的演示：终端里的文字仍然是文字，可以选中复制，本页这段近两分钟的安装片段约 110 KB。图形界面的操作用截图或视频，本组件只播放终端录像。播放器与样式随主题分发，构建期不下载、运行期不连 CDN，只有用到它的页面加载这套运行时。

## 最简例子 {#minimal}

只有 `file` 是必填的：

```markdown {title="源码"}
{{</* asciinema file="images/install.cast" */>}}
```

{{< asciinema file="images/install.cast" >}}

这段录像是 Pigsty 在一台 Debian 机器上的单机安装，120×36 的终端，截取了开头约 1 分 54 秒。文件在本站的 `static/images/install.cast`，路径写站点根路径。放在 `assets/` 下也写相对路径：主题先在资源里查找，找不到再当成站点根路径。不写 `title` 时，窗口标题显示 `file` 的值。

## 窗口标题与主题 {#title-theme}

`title` 设置窗口标题，`theme` 设置配色：

```markdown {title="源码"}
{{</* asciinema file="images/install.cast" title="Pigsty 单机安装" theme="dracula" */>}}
```

{{< asciinema file="images/install.cast" title="Pigsty 单机安装" theme="dracula" >}}

`theme` 默认 `auto`：跟随站点的深浅色，浅色用 `td-light`，深色用 `td-dark`，读者切换配色时播放器就地重挂一次。要固定成某套终端配色时，可选值是播放器自带的 `asciinema`、`dracula`、`gruvbox-dark`、`monokai`、`nord`、`seti`、`solarized-dark`、`solarized-light`、`tango`，以及主题提供的 `td-light` / `td-dark`。固定的主题不跟随深浅色，深色站点配 `solarized-light` 的对比度不合适。终端字体不用单独设置：播放器使用站点的代码字体，与页面上的代码块一致。

## 速度、起点与封面 {#playback}

长录像用三个参数控制起点：`speed` 设倍速，`startAt` 跳过开头，`poster` 决定未播放时定格的画面。

```markdown {title="源码"}
{{</* asciinema file="images/install.cast" title="从第 60 秒开始，两倍速"
  speed="2" startAt="60" poster="npt:1:30" */>}}
```

{{< asciinema file="images/install.cast" title="从第 60 秒开始，两倍速" speed="2" startAt="60" poster="npt:1:30" >}}

`speed` 与 `startAt` 是数字（秒），`poster` 用播放器的 `npt:` 记法定位时间点，`npt:1:30` 是第 1 分 30 秒。上面这个播放器停在第 90 秒的画面，点播放从第 60 秒开始。

`idleTimeLimit` 把静默段压缩到最多 N 秒。这段录像在录制时已经压缩过（`.cast` 头里是 `idle_time_limit: 0.5`），此处不必再设。只有录制时没有限制静默时长的文件才需要它。

## 尺寸与适配 {#size}

播放器默认按容器宽度缩放（`fit="width"`），终端的行列数来自 `.cast` 文件头。`cols` / `rows` 可以覆盖它：

```markdown {title="源码"}
{{</* asciinema file="images/install.cast" title="只留 16 行高" rows="16" */>}}
```

{{< asciinema file="images/install.cast" title="只留 16 行高" rows="16" >}}

比录像本身小的行列数会裁掉内容，上面这个只显示 36 行里的 16 行。`cols` / `rows` 用于修正录像头里的错误尺寸，不是排版工具。要让播放器变矮，重录一次小终端。

`fit` 的四个值：`width`（默认，按宽度缩放）、`height`（按高度）、`both`（两个方向都装下）、`none`（不缩放，按字号原样显示，宽终端会溢出）。

## 循环与预加载 {#autoplay}

`loop` 播完自动重播，`preload` 在页面加载时取回 `.cast`，点播放不必等待：

```markdown {title="源码"}
{{</* asciinema file="images/install.cast" title="循环播放：登录后的第一分钟"
  startAt="0" speed="3" loop="true" preload="true" */>}}
```

{{< asciinema file="images/install.cast" title="循环播放：登录后的第一分钟" startAt="0" speed="3" loop="true" preload="true" >}}

`autoplay="true"` 让页面打开即播。不建议使用：系统的「减少动态效果」偏好只关闭播放器控件的过渡动画，不阻止自动播放。确实需要自动播放时，配上 `loop`、很短的内容，并且一页只放一个。

## 放进步骤里 {#in-steps}

录像放在某一步旁边：文字说明要做什么，录像展示实际输出。

````markdown {title="源码"}
1. 安装依赖，获取安装脚本：

   ```sh
   curl -fsSL https://repo.pigsty.io/get | bash
   ```

2. 执行安装，这里是开头的两分钟：

   {{</* asciinema file="images/install.cast" title="pig install" speed="4" */>}}

3. 打开 `http://<节点地址>:3000`，用 `admin / pigsty` 登录 Grafana。
{.steps}
````

1. 安装依赖，获取安装脚本：

   ```sh
   curl -fsSL https://repo.pigsty.io/get | bash
   ```

2. 执行安装，这里是开头的两分钟：

   {{< asciinema file="images/install.cast" title="pig install" speed="4" >}}

3. 打开 `http://<节点地址>:3000`，用 `admin / pigsty` 登录 Grafana。
{.steps}

一页可以放多个播放器，脚本与样式只加载一次。

## 录制 cast 文件 {#recording}

主题只负责播放。用 [asciinema](https://docs.asciinema.org/) 的 `asciinema rec --idle-time-limit=2 --cols=100 --rows=28 install.cast` 录制，`asciinema play install.cast` 本地回放确认。

- 终端宽度控制在 100 列以内，窄屏上仍可读；录制前先 `clear`。
- 录制前清理密钥：`.cast` 是纯文本，录像里的每个字符都能 `grep` 到，提交前检查一遍。
- 文件放进 `static/images/` 或页面包并提交进仓库，不引用外站的 `.cast` URL。

## 输出形态 {#outputs}

| 输出 | 呈现 |
| --- | --- |
| HTML | `<div class="td-asciinema">` 窗口外框 + 播放器；播放器 CSS/JS 与初始化脚本按需加载，一页一次 |
| 打印 | 同 HTML（打印输出也加载播放器）；印到纸上只会留下当时的一帧 |
| Markdown | 同一段容器 HTML 加一个 JSON 配置块；纯文字里能读到的只有窗口标题 |
| RSS | 同一段静态标记；阅读器不执行脚本，只剩一个空窗口外框 |

录像不能是唯一的信息来源。关键命令与关键输出要在录像旁边用文字或代码块写一遍：离线读者、`llms.txt` 的抓取方与打印读者只能看到这些文字。

## 参数参考 {#reference}

| 参数 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `file` | 路径（必填） | — | 具名或第一个位置参数；先按全局资源找，找不到当站点根路径；带协议的完整 URL 原样透传 |
| `title` | 纯文本 | `file` 的值 | 窗口标题 |
| `theme` | 枚举 | `auto` | `auto` 跟随站点深浅色；或 `td-light` `td-dark` `asciinema` `dracula` `gruvbox-dark` `monokai` `nord` `seti` `solarized-dark` `solarized-light` `tango` |
| `fit` | 枚举 | `width` | `width` `height` `both` `none`；其它值构建失败 |
| `cols` / `rows` | 整数 | 来自 `.cast` 文件头 | 覆盖终端行列数；比录像小会裁掉内容 |
| `speed` | 数字 | `1` | 播放倍速 |
| `startAt` | 数字（秒） | `0` | 起播位置 |
| `idleTimeLimit` | 数字（秒） | 来自 `.cast` 文件头 | 静默段最多播这么久 |
| `poster` | 字符串 | — | 未播放时定格的画面，`npt:分:秒` |
| `autoplay` | `"true"` / 不写 | 关 | 页面加载即播；不建议 |
| `loop` | `"true"` / 不写 | 关 | 循环播放 |
| `preload` | `"true"` / 不写 | 关 | 页面加载时就取回 `.cast` |
| `pauseOnMarkers` | `"true"` / 不写 | 关 | 播到章节标记处暂停 |
| `markers` | `时间:标签,时间:标签` | — | 章节标记；见下面的限制，标签目前到不了播放器 |
{.fields meta="type default"}

布尔类参数比较的是文本 `true`：`loop="true"` 与 `loop=true` 都表示开启，其它值表示关闭。`fit` 的取值由主题校验，非法值报错并给出参数名。数字类参数（`speed` `cols` `rows` `startAt` `idleTimeLimit`）写成非数字会在转换时让构建失败。

## 限制与常见问题 {#limits}

- `markers` 的标签会丢失：主题把 `时间:标签` 的列表拼成一维数组交给播放器，播放器只接受成对写法，时间轴上会多出没有标签的标记点。需要章节时用录像旁边的文字列表。
- 播放器需要 JavaScript：禁用脚本时，以及 Markdown 与 RSS 输出里只有一个空窗口，见[输出形态](#outputs)。
- 录像不进搜索：站内搜索索引页面文字，录像里出现过的命令搜不到。
- 不引用远程 `.cast`：`file` 收到带协议的 URL 会原样透传给播放器，页面因此依赖一个外站。
- 控制单段长度：超过五六分钟的录像少有人看完，长流程拆成几段短录像，各配一段文字。

## 相关 {#related}

- [代码块](/zh/docs/code/) — 关键命令与输出写成可复制的代码块
- [步骤](/zh/docs/steps/) — 把录像放在某一步旁边
- [图片](/zh/docs/image/) — 静态截图；终端内容优先用录像，图形界面用截图
- [引用](/zh/docs/include/) — 同一段命令要在几页复用时
