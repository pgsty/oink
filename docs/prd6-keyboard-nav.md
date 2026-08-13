# PRD 6 · 键盘导航（Keyboard Navigation）— 设计方案

状态：**已评审 · v2** —— 开放问题已于 2026-08-13 裁决（§11）；
同日第三轮实测反馈重设了键位体系（§12，本文各节已按 v2 更新）

日期：2026-08-13

范围：shell 布局（docs / blog / swagger）下的全站单键键盘导航：
侧栏树焦点导航（WASD / 方向键）、目录跳转与翻页（j/k、q/e）、
外观与语言切换（h/l/t）、面板快捷键（f/c 与 `/`、`\`），以及
fat footer 的折叠箭头。

前置阅读：`docs/prd4-navigation-command-palette-contract.md`、`CLAUDE.md`

本文遵循 PRD 惯例：允许讨论与取舍；评审后公共决策冻结进 contract
文档并配套 `scripts/check-*.py` 机器检查，任务分解落入本地 `plan/`。

---

## 0. TL;DR

给 OINK 增加一套 Vim 风格 + 十字键的纯键盘导航，**默认开启**，
可全局（或经 front-matter cascade 按节）关闭：

| 键                                         | 行为                                                          |
| ------------------------------------------ | ------------------------------------------------------------- |
| `w` `s`（全局，一步到位）/ `↑` `↓`（树内） | 侧栏树焦点上移 / 下移（首按即从当前页锚点移动）               |
| `a` `d`（全局，一步到位）/ `←` `→`（树内） | 折叠 / 展开（ARIA tree 语义；首按直接作用于当前页所在项）     |
| `Enter` `Space` `g`（树内）                | 前往当前焦点项                                                |
| `Escape`（树内）                           | 退出树焦点，返回正文                                          |
| `q` `e`（全局）                            | 上一篇 / 下一篇（侧栏树序）                                   |
| `j` `k`（全局）                            | 沿右侧页面目录跳到下一节 / 上一节（无目录页面退化为平滑滚动） |
| `h`（全局）                                | Hide：隐藏/恢复左右栏与页脚（禅模式，会话内跨页记忆）         |
| `l`（全局）                                | Language：循环切换可用语言                                    |
| `t`（全局）                                | Theme：亮/暗模式切换                                          |
| `f`（全局）                                | 同 `/`：打开命令面板**完整搜索态**                            |
| `c`（全局）                                | 同 `\`：打开命令面板**纯命令态**                              |
| `/` `\`（全局）                            | 搜索态 / 命令态（属搜索功能，不受键盘导航开关影响，见 §6.1）  |
| `?`                                        | **保留不占用**（未来快捷键帮助浮层）                          |

配套交付：fat footer 的版权行右端新增**折叠箭头**，可收起/展开上方的
链接栅格，选择经 localStorage 跨页持久（§6.4）；`h` 键的禅模式则把
左右栏、页脚与浮动按钮一并隐藏。原 `c`=复制 Markdown 快捷键在 v2 中
移除（复制仍可经页面动作按钮与命令面板触达）。

核心架构决策：**不建平行体系**。所有能力都接在既有机制上——
树的展开/折叠走 `docs-shell.js` 的 chevron 按钮，`/` `\` 落在
`command-palette.js` 内部并暴露 `OinkCommandPalette.instance` 供
f/c 复用，`l`/`t` 走 `OinkActions` 的 `switch_language` /
`switch_theme` 动作，j/k 以 `#TableOfContents` 为目录数据源，
装配走 `_partials/scripts.html` 的参数门控 + `$bundleKey`。
键盘主体集中在 `assets/js/keyboard-nav.js`；footer 折叠箭头独立为
`footer-collapse.js`（不依赖键盘导航开关）。

新增 i18n key：**2 个**（`ui_footer_collapse` / `ui_footer_expand`，
en 与 zh/zh-cn/zh-tw 人工翻译，其余 locale 经 `check-i18n.py --sync`）。

---

## 1. 背景与已裁决要点

用户侧（oink.pgsty.com 维护者）已裁决四点，本文视为约束：

1. **可配置，默认开启**。`params.ui.keyboard_nav.enable`，主题默认 `true`。
2. **`?` 帮助浮层保留**：在全部快捷键设计定稿前不实现，但键位为其留空。
3. **输入焦点绝对让行**：任何输入类焦点（input / textarea / select /
   contenteditable / IME 组字）存在时，全部单键快捷键必须禁用。
4. **静态站语义**：树内移动只移焦点、不换页；`Enter` / `Space` / `g`
   才触发整页跳转。实现全部落在 OINK 主题仓库。

现状盘点（实现起点）：

- `command-palette.js` 已有 `Cmd/Ctrl+K` 与 `/` 快捷键、`>` 命令前缀、
  `isTypingTarget` 守卫、IME 守卫（`isComposing || keyCode === 229`）。
  **注意**：当前 `/` 打开的是**命令态**（`open(event, COMMAND_PREFIX)`），
  与本设计的目标语义相反，需要契约修订（§6.1）。
- `action-registry.js` 暴露 `global.OinkActions`，内建 `copy_markdown`
  动作与剪贴板降级；manifest 经 `#oink-action-manifest` JSON 注入。
- `docs-shell.js` 维护树 chevron（`[data-td-shell-tree-toggle]`）的
  `aria-expanded` / `aria-label` / 展开动画；`sidebar-nav.js` 负责
  缓存树的 active path 水合。
- 侧栏树 DOM：`nav.td-shell-tree` → `li.td-shell-tree__item`
  （`has-child` / `leaf` / `--hidden`）→ `div.td-shell-tree__row` →
  `a.td-shell-tree__link` + 可选 chevron 按钮 →
  `div.td-shell-tree__children`（`is-open` / `--static`）。
- docs 页当前**没有** pager（PRD 5 track 5.1 才引入卡片式树序 pager，
  0.4 里程碑）；blog 有 `_partials/pager.html`（`PrevInSection` 语义）。
- 正文滚动容器是 window（无内层 overflow 容器）；侧栏自有滚动区。

---

## 2. 键位总表与作用域模型

作用域分两级：

- **全局**（focus 在页面任意非输入位置）：`w s a d q e j k h l t f c`，
  以及 `/` `\`（面板自有）。
- **树内**（focus 位于 `nav.td-shell-tree` 内部）：方向键、
  `Enter`、`Space`、`g`、`Escape`（WASD 继续生效）。

设计原则：**方向键绝不做全局劫持**。`↑↓←→` 只在焦点已进入树内时
生效（标准 ARIA tree 行为），树外保持浏览器原生滚动。WASD 是
"全局遥控器"且**一步到位**（v2，§12.1）：焦点在正文时按 `w`/`s`，
以当前页所在项为锚点直接移动一格并落焦；`a`/`d` 直接对当前页所在项
执行折叠/展开。后续按键在树内继续。

| 键        | 作用域             | 行为                                                      | 冲突/备注                               |
| --------- | ------------------ | --------------------------------------------------------- | --------------------------------------- |
| `w` / `↑` | 全局（一步）/ 树内 | 焦点移到上一个**可见**项                                  | 到顶后驻留（不回绕）                    |
| `s` / `↓` | 全局（一步）/ 树内 | 焦点移到下一个可见项                                      | 到底后驻留                              |
| `a` / `←` | 全局（一步）/ 树内 | 已展开 → 折叠；已折叠或叶子 → 焦点移到父项                | ARIA APG tree 语义                      |
| `d` / `→` | 全局（一步）/ 树内 | 已折叠 → 展开；已展开 → 焦点移到第一个子项；叶子 → 无操作 | 同上                                    |
| `Enter`   | 树内               | 前往焦点项链接                                            | 链接原生行为，零代码                    |
| `Space`   | 树内               | 前往焦点项链接                                            | `preventDefault` 阻止翻屏后 `click()`   |
| `g`       | 树内               | 前往焦点项链接                                            | 与未来 `gg` 序列的关系见 §11.3          |
| `Escape`  | 树内               | 焦点返回正文（触发前元素或 blur）                         | drawer 开启时让行给 docs-shell          |
| `j`       | 全局               | 目录下一节（Vim 语义：j 下 k 上）                         | 无目录页退化为 +300px 缓动滚动          |
| `k`       | 全局               | 目录上一节；深入节内时先回本节起点                        | 无目录页退化为 -300px 缓动滚动          |
| `q`       | 全局               | 上一篇（树序）                                            | 无上一篇则静默                          |
| `e`       | 全局               | 下一篇（树序）                                            | 无下一篇则静默                          |
| `h`       | 全局               | Hide：禅模式开关（左右栏 + 页脚 + 浮动按钮）              | sessionStorage 跨页记忆                 |
| `l`       | 全局               | Language：循环切换语言                                    | 单语言站静默                            |
| `t`       | 全局               | Theme：亮/暗切换                                          | 暗色菜单关闭时静默                      |
| `f`       | 全局               | 面板完整搜索态（同 `/`）                                  | 无本地搜索时静默                        |
| `c`       | 全局               | 面板纯命令态（同 `\`）                                    | v1 的 c=复制已移除（§12.2）             |
| `/`       | 全局               | 面板完整搜索态（命令垫底、序同导航栏）                    | **语义变更**，契约修订 §6.1             |
| `\`       | 全局               | 面板纯命令态（预填 `>`）                                  | 部分键盘布局取 `\` 不便，`>` 前缀恒可用 |
| `?`       | —                  | **保留**                                                  | 未来帮助浮层                            |

明确保留、v2 不占用：`?`（帮助）、`gg` / `Shift+G`（未来顶部/底部）、
数字键。任何新增键位须先修订本表。

---

## 3. 全局守卫（何时全部禁用）

每个 keydown 处理器按序短路，条件与 `command-palette.js` 现行
`/` 守卫完全一致并扩展：

1. `event.isComposing || event.keyCode === 229` —— IME 组字中
   （中文站硬约束）。
2. `isTypingTarget(event.target)` —— input / textarea / select /
   `[contenteditable]:not([contenteditable="false"])`（复用 palette
   同款谓词；keyboard-nav 内部自持一份副本，因 palette 仅在
   `$localSearch` 时装配，keyboard-nav 不得依赖它存在）。
3. `event.ctrlKey || event.metaKey || event.altKey || event.shiftKey` ——
   带修饰键的组合（如 `Cmd+C`、`Shift+方向键`）一律放行给浏览器。
4. `event.defaultPrevented` —— 已被其他组件消费。
5. 命令面板开启（`[data-td-shell-search]` 处于 open 态）或焦点位于
   `dialog[open]` / `[role="dialog"]` 内 —— 让行给弹层自身键盘逻辑
   （面板、image-zoom、page-actions 弹层等）。
6. 配置关闭 —— 模块根本不装配（§7），无运行时判断成本。

Giscus 评论框在 iframe 内，键事件不冒泡到父文档，天然隔离。

---

## 4. 侧栏树焦点导航

### 4.1 焦点模型：真实 focus，不动 Tab 序

v1 **不安装** roving tabindex、不加 `role="tree"`：那会改变现有
`nav` + 链接列表对所有用户（含屏幕阅读器存量用户）的语义与 Tab
行为，风险大于收益。方案：

- WASD/方向键直接对目标 `a.td-shell-tree__link` 调
  `focus({ preventScroll: true })` + `scrollIntoView({ block: 'nearest' })`
  （侧栏自有滚动区）。
- 真实 focus 意味着屏幕阅读器免费朗读链接名与 `aria-current`，
  `Enter` 是链接原生行为。
- **高亮即选中，不是方框**（2026-08-13 评审反馈修订）：模块把
  `.td-kbd-focus` 类挂在焦点项所在的整行 `.td-shell-tree__row` 上，
  样式为行级背景色 `rgba(link-color, 0.16)` —— 与 active 项的
  `--td-shell-primary-dim`（0.1）同色系但深一档，"当前页"与
  "键盘光标"一眼可辨；不使用 outline。`forced-colors` 下背景色失效，
  降级为 `outline: 2px solid Highlight`。类在 Escape、焦点移出该行
  （`focusin` 监听）时移除。之所以需要此类：程序化 `focus()` 在部分
  浏览器不触发 `:focus-visible`。
- 完整 ARIA tree pattern（role=tree + roving tabindex）记为未来
  可选升级，届时另立契约条目。

### 4.2 可见项扁平化

每次按键即时计算（树被 `sidebar_menu_truncate` 上限约束在 ≤2000
节点，`querySelectorAll` 一次遍历可忽略不计，无需缓存失效逻辑）：

> 可见链接 = `#td-sidebar-menu` 内所有 `a.td-shell-tree__link`，
> 过滤掉：所属 `li` 带 `--hidden`；或任一祖先
> `.td-shell-tree__children` 既非 `is-open` 也非 `--static`。

该扁平序列同时服务 `w/s` 移动与 `q/e` 翻页（§5.2）——一个模型
两处使用，保证"焦点移动顺序"与"翻页顺序"永远一致。

### 4.3 展开 / 折叠

`a` / `d`（及 `←` / `→`）不自己改 DOM，而是定位焦点项所在
`.td-shell-tree__row` 的 chevron（`[data-td-shell-tree-toggle]`）并
程序化 `click()`——`aria-expanded`、`aria-label` 翻转、展开动画、
与 `docs-shell.js` 的既有状态维护全部复用，零重复实现。
无 chevron（`sidebar_menu_foldable` 关闭或叶子节点）时按 ARIA
语义退化为"移向父项 / 无操作"。

RTL（红线 6）：`←` / `→` 语义按 `dir` 反转（APG 惯例）；
`a` / `d` 恒等于"折叠 / 展开"物理语义，不反转。

### 4.4 树不可见时

**已裁决（§11.1）**：移动端 drawer 关闭时，首按 `w/s/a/d` 打开侧栏
抽屉（复用 `docs-shell.js` 既有 drawer 开启路径）并把焦点落到树的
active 项；后续按键正常导航。页面根本没有侧栏树（如 swagger 局部页）
时静默 no-op。

---

## 5. 内容键：目录跳转与翻页

### 5.1 `j` / `k` 目录跳转（v2，§12.3）

j/k 不再是纯滚动，而是**沿页面目录（右栏 TOC）逐节跳转**：

- 目标序列取 `#TableOfContents` 内锚点指向的标题元素（与右栏目录
  完全同源）；无 TOC 时回退 `.td-shell-main` 内的 `h2-h4[id]`，
  两者都没有（无标题页面）则退化为 ±300px 缓动滚动。
- "当前节" = 视口读线（`--td-shell-nav-h` + 24px）之上最近的标题。
  `j` 跳下一节起点；`k` 跳上一节起点，**深入节内超过 40px 时先回
  本节起点**（媒体播放器的"上一曲"语义）；再往上越过第一节则回
  页面顶部并清除 hash。
- 跳转用与滚动同一套缓动引擎（`SCROLL_EASE = 0.28` 指数收敛），
  `prefers-reduced-motion` 时瞬时定位；落点经
  `history.replaceState` 同步 `#hash`，不产生历史条目。

### 5.2 `q` / `e` 翻页数据源（v2 由 h/l 迁移，§12.4）

按优先级解析，取第一个命中：

1. `head` 内 `link[rel="prev"]` / `link[rel="next"]` ——
   **为 PRD 5 track 5.1 预留的对接点**：树序卡片 pager 落地后若同时
   输出 rel link，键盘翻页自动与其同源，无需改本模块。
2. docs shell：§4.2 扁平序列中定位当前页（`a.active` 或 canonical
   路径匹配，与 `sidebar-nav.js` 同法）取前后项 —— 即"侧栏树序"，
   与 5.1 的排序口径一致。
3. blog：现有 `pager.html` 的前后按钮 `href`（`data-td-pager-*`
   钩子，跳过 `disabled`）。

无目标（第一篇按 `q`、最后一篇按 `e`、无树无 pager 页面）→
静默 no-op，零新增文案。

---

## 6. 面板与动作键

### 6.1 `/` 与 `\`：落在 command-palette.js，含契约修订

实现位置：`command-palette.js` 全局 keydown 处（紧邻现有 `/`
分支），**不在** keyboard-nav.js —— 面板快捷键必须与面板同生共死
（仅 `$localSearch` 装配时存在），且不受 `ui.keyboard_nav.enable`
开关影响（`/` 是既有能力，关掉键盘导航不应弄丢搜索入口）。

**已裁决**语义：

- `/` → `open(event)`（完整搜索面板）。可搜页面、也可选命令；
  命令类分组**垫底**，顺序与导航栏菜单一致。**这是行为变更**：现行
  contract 明文 "The slash shortcut opens directly in command-only
  mode"（`prd4-navigation-command-palette-contract.md`）。
- `\` → `open(event, COMMAND_PREFIX)`（纯命令面板：只列命令，
  没有页面搜索的概念；输入文本仅过滤命令）。守卫与 `/` 完全同款
  （`!isOpen && !isTypingTarget && 无修饰键`）。

**命令排序对齐导航栏**（导航栏实序：主菜单 → 版本 → 搜索 →
语言 → 主题 → GitHub；面板即搜索本体，quick links 即主菜单）：

1. `actions/context.html` 的偏好三连（choice 动作）由
   `switch_theme, switch_language, switch_version` 重排为
   `switch_version, switch_language, switch_theme`；`open_github`
   维持其后。三者均为 `paletteOnly`，不影响页面动作栏。
2. `palette-model.js` `actionRows`：内建动作（manifest 序）在前，
   站点配置命令（`registry.commands()`）在后 —— 导航栏有锚点的
   项先行，站点自定义命令殿后，配置内相对顺序保持。
3. 空查询的命令态不再按标题字母序（现行 `rank('')` 副作用），
   改为保持 manifest 序，与 `/` 空态的分组顺序一致。

文本查询下仍按相关度排序（快捷键排序约束只作用于浏览态列表）。

按红线 7，契约与行为同一原子变更：同 commit 内修订 contract 文档
该段落 + 同步 `scripts/check-prd4-palette.py`（如其断言涉及 seed）+
`tests/js/prd4-command-palette.test.js`、`prd4-palette-model.test.js`
相应用例。机器契约 `tests/fixtures/prd4/contract.json` 的
`palette.modes` 与 `command_prefix` 不变，无需修改。

已知限制：`\` 在部分非 US 布局需组合键；面板内 `>` 前缀恒可用，
文档注明即可。

### 6.2 `f` / `c`：面板的键盘导航别名（v2，§12.2）

`command-palette.js` 在自动初始化时暴露
`OinkCommandPalette.instance`（及 `commandPrefix`），keyboard-nav
借此实现 `f` = 搜索态、`c` = 命令态，与 `/` `\` 完全同一实例、
零对话框逻辑重复。面板未装配（`offlineSearch` 关闭）时 f/c 静默且
不吞字符。**v1 的 `c`=复制 Markdown 快捷键随之移除**：复制仍可经
标题旁的页面动作按钮与面板内的 `copy_markdown` 命令触达；随复制
一起引入的 toast 组件亦一并撤除（当前无消费者）。

### 6.3 `h` / `l` / `t`：外观与语言（v2，§12.5）

- **`h` = Hide（禅模式）**：在 `<html>` 上切换 `data-td-kbd-zen`，
  CSS 一次性隐藏 navbar 或 navbar-off 的 compact subnav、
  `#td-shell-sidebar`、`.td-shell-toc`、`.td-shell-float` 与
  `[data-td-shell-footer]`；flex 布局让正文列自然占满。状态存
  sessionStorage（键 `td-kbd-zen`），由 head 中的 prepaint 在首帧前恢复，
  `q/e` 翻页后无闪烁；关标签页即忘。禅模式中 WASD 不会把焦点送进
  隐藏的侧栏。
- **`l` = Language**：读 `switch_language` 动作的 options（含每语言
  当前页 URL 与 active 标记），循环跳到下一个可用语言；单语言站
  action 不可用，静默。
- **`t` = Theme**：读 `<html data-bs-theme>` 现值，经
  `OinkActions.run('switch_theme', {value})` 在 light/dark 间翻转
  （dark-mode.js 的既有 executor 负责存储与广播）；暗色菜单未启用时
  静默。

### 6.4 fat footer 折叠箭头（v2，§12.6）

独立于键盘导航的配套交付（`footer-collapse.js`，fat footer 存在时
才装配）：

- 版权行（`.td-shell-footline`）右端新增 chevron 按钮
  （`data-td-footer-toggle`，`aria-expanded` + `aria-controls`
  指向 `#td-site-footer`），点击折叠/展开上方链接栅格；折叠时
  图标旋转 180° 指回上方。
- 默认展开；选择存 localStorage（键 `td-footer-collapsed`）跨页持久。
- 文案 i18n：`ui_footer_collapse` / `ui_footer_expand`（新增 ×32
  locale）。footer 高度变化由 docs-shell 既有 ResizeObserver 自动
  重算 `--td-shell-footer-offset`。
- 与 `h` 键正交：箭头只管 fat 栅格，禅模式隐藏整个 footer；
  两个状态互不覆盖。

---

## 7. 配置与装配

```yaml
params:
  ui:
    keyboard_nav:
      enable: true # 主题默认开启；false 时 JS 不装配
```

- 读取用 `.Param "ui.keyboard_nav.enable"`（页面级 lookup）——
  免费获得 front-matter / cascade 按页、按节关闭能力（比如某个
  交互密集的演示页）。
- `_partials/scripts.html`：
  `$hasKeyboardNav := and $shell (ne (.Param "ui.keyboard_nav.enable") false)`；
  命中则 `$jsArray | append (resources.Get "js/keyboard-nav.js")`，
  并把 `$hasKeyboardNav` 加入 `$bundleKey`（红线 4）。
  仅 shell 布局（docs / blog / swagger）装配；landing 无侧栏树、
  无翻页语义，不装配。
- keyboard-nav.js 排在 docs-shell.js 之后追加（逻辑上事件驱动 +
  惰性查询，实际无硬顺序依赖，但保持"依赖者靠后"惯例）。
- local-first（红线 5）：零网络、零第三方依赖，纯 vanilla IIFE，
  风格对齐 `navbar-menu.js` / `page-actions.js`。

---

## 8. 无障碍与国际化

- 真实 focus 导航（§4.1），SR 朗读免费；不引入 aria-activedescendant
  虚拟焦点。
- 树外不劫持方向键 / Space / Enter，原生滚动与激活行为不变。
- `.td-kbd-focus` 焦点高亮在 forced-colors 下回退为系统色描边；
  滚动动画尊重 prefers-reduced-motion。
- RTL：方向键随 `dir` 反转（§4.3）；逻辑属性书写样式（红线 6）。
- i18n：v1 **零新增 key**。若评审加入边界提示 / drawer 提示，
  则新 key × 32 locale，en 与 zh 系人工翻译（红线 3）。
- 输出矩阵（红线 2）：本特性纯运行时 JS，仅随 html 输出装配；
  print / markdown / rss 无变化（scripts.html 既有门控已覆盖）。

---

## 9. 测试与机器检查

主题仓库：

- `tests/js/prd6-keyboard-nav.test.js`（仿 prd4 系测试）：
  守卫谓词（IME / 输入焦点 / 修饰键 / 弹层开启）、扁平化过滤、
  `a/d` 状态机（展开→折叠→父项）、`h/l` 三级数据源解析、
  边界驻留（顶/底不回绕）。
- `tests/js/prd4-command-palette.test.js`：`/` 搜索态、`\` 命令态
  用例更新。
- 新增 `scripts/check-prd6-keyboard.py`：断言 scripts.html 门控与
  `$bundleKey` 项存在、`hugo.yaml` 默认值为 true、契约键位表与
  `keyboard-nav.js` 键位常量一致、无孤儿 i18n key。
- 既有基线全序列（CLAUDE.md「Commands」）+ exampleSite 构建全绿。

站点仓库（oink.pgsty.com）：

- `tests/browser` Playwright 用例：`s` 键焦点进树并逐项下移；
  `d` 展开分组；`Enter` 跳转；`q/e` 按树序翻页；`/` 与 `f` 开面板
  搜索态、`\` 与 `c` 开命令态；焦点在搜索输入框内按 `j` 页面不滚动；
  修饰键、可见 dialog、折叠侧栏、禅模式与窄屏 drawer 均覆盖。

---

## 10. 交付物清单

| #   | 交付物                                                             | 位置                                                           |
| --- | ------------------------------------------------------------------ | -------------------------------------------------------------- |
| 1   | `keyboard-nav.js`（守卫 + 树焦点 + 目录跳转/翻页 + 外观/面板动作） | 主题 `assets/js/`                                              |
| 2   | 装配 + `$bundleKey`                                                | 主题 `_partials/scripts.html`                                  |
| 3   | `ui.keyboard_nav.enable: true` 默认值                              | 主题 `hugo.yaml`                                               |
| 4   | `/` `\` 变更 + PRD 4 契约修订 + check/test 同步（同一原子变更）    | 主题 `command-palette.js` / `docs/` / `scripts/` / `tests/js/` |
| 5   | `.td-kbd-focus` 焦点高亮 + 禅模式样式                              | 主题 `assets/scss/`                                            |
| 6   | `prd6-keyboard-nav.test.js` + `check-prd6-keyboard.py`             | 主题 `tests/js/` / `scripts/`                                  |
| 7   | CHANGELOG 条目 + exampleSite 配置示例                              | 主题                                                           |
| 8   | 快捷键说明文档页（en + zh）                                        | 站点 `content/docs/`                                           |
| 9   | Playwright 集成用例                                                | 站点 `tests/browser/`                                          |
| 10  | `plan/0.x/` 任务分解（评审通过后）                                 | 主题本地 plan 工作区                                           |

里程碑归属：本特性无外部依赖，可独立发布；与 PRD 5 track 5.1
（0.4 树序 pager）仅有一个自愿对接点（rel link，§5.2-1）。建议随
0.4 同行或单列 0.3.x 小版本，由维护者裁决（§11.5）。

---

## 11. 开放问题 —— 2026-08-13 逐条决议

1. **移动端 drawer**：**已裁决** —— 移动端本无键盘，此场景边缘；
   若硬件键盘存在，树不可见时首按 `w/s/a/d` 打开抽屉并聚焦
   active 项（§4.4）。
2. **边界反馈**：**按建议通过** —— v1 静默（零文案、零新 i18n
   key）；帮助浮层设计时一并复议。
3. **`g` 与 Vim 序列**：**按建议通过** —— v1 `g` 单击=前往树焦点
   项；若未来引入 `gg`/`Shift+G`，届时改带序列窗口，行为兼容。
4. **`j/k` 步长**：**二次裁决（2026-08-13 实测反馈）** —— 110px
   instant 太慢且不丝滑，改为 300px/按键 + 缓动动画（§5.1），
   常量仍收在模块顶部。
5. **里程碑**：随下一个发布（维护者排期，无技术约束）。
6. **`/` 语义变更**：**已裁决必改** —— `/`=完整搜索面板（命令垫底、
   序同导航栏），`\`=纯命令面板；CHANGELOG 显著标注，不做兼容
   开关（`>` 前缀仍达命令态）。

---

## 12. 第三轮修订 —— 2026-08-13 键位体系 v2

实测后维护者重设键位，本文各节已按以下决议更新：

1. **WASD 一步到位**：取消"首按只进树"，首按即以当前页所在项为
   锚点移动/操作；drawer 场景保持"首按开抽屉落焦不移动"（开抽屉
   已是一次可感知的状态变化，再叠加移动会失去方位感）。
2. **`c` 改为命令面板**（Command），`f` 同 `/`（Find）；
   `c`=复制快捷键与配套 toast 移除，复制经页面动作按钮/面板可达。
3. **`j`/`k` 改为目录逐节跳转**（右栏 TOC 同源），无目录页退化为
   缓动滚动；`k` 深入节内时先回本节起点。
4. **`q`/`e` 接管上一篇/下一篇**（原 h/l），键位与 WASD 同手，
   翻页语义与树序一致。
5. **`h`=Hide 禅模式、`l`=Language、`t`=Theme**：三个单键状态开关，
   全部复用既有机制（zen 为纯 CSS 隐藏；语言/主题走 action registry）。
6. **fat footer 折叠箭头**：版权行右端 chevron 收起/展开链接栅格，
   localStorage 持久，默认展开；独立于键盘导航开关。
