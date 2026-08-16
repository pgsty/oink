# PRD 7 · Docs / Blog 阅读外壳与页尾体系

状态：**已实现（本地）**

日期：2026-08-15
范围：OINK 主题及 `oink.pgsty.com` 样例站的 Docs / Blog 导航、键盘序列、
taxonomy 菜单、正文页尾组件，以及低摩擦的结构化文档反馈。

四张 Fumadocs 截图仅作为视觉与交互参考；本 PRD 的文字约束与 OINK
既有 Hugo 数据模型才是实现依据。

---

## 0. 目标

Docs / Blog 应更像一个以左侧信息架构为主的阅读工具，而不是把顶栏、
侧栏、正文和页尾做成四套彼此竞争的导航。实施后：

1. 左侧导航栏在桌面端覆盖顶栏左侧，顶部固定显示站点标识、收起按钮，
   其下显示栏目切换器；顶栏仍负责全站入口与工具。
2. 栏目切换器默认存在，包含所有顶级栏目和所有
   `sidebar_root_for: self` 的独立栏目；只有一个入口时显示无背景链接。
3. 当前栏目根页面是侧栏序列的第一个可选文档，W/S 与 Q/E 均可到达。
4. taxonomy 顶栏菜单显示按数量降序排列的 `Tag + count` 标签网格。
5. 文末固定为 Feedback → Annotation → Pager → Comments，四者独立开关。
6. `y` 与 `l` 都是全局语言切换键。
7. OINK 提供无需登录、无需后端的一键反馈；详细文字继续交给同页 Giscus。

非目标：复刻 Fumadocs 的 React 组件、把 Giscus iframe 当作任意表单 API、
收集自由文本，或由 OINK 运营集中式评论/反馈服务。

---

## 1. 导航信息架构

### 1.1 左栏优先级

桌面端侧栏从视口顶部开始，层级高于站点顶栏。其固定头部依次为：

1. 站点 icon / wordmark、搜索按钮与侧栏收起按钮；搜索始终紧邻收起按钮左侧；
2. 配置在线搜索时使用独立搜索行；
3. 栏目切换器；
4. 导航树。

侧栏底部固定保留全局工具坞：语言与版本靠左，亮暗主题与 GitHub 靠右，不随
中间导航树滚动，并在最小桌面宽度与移动 drawer 中保持完整可见。语言、版本、
主题菜单均向上展开；版本 hover 即打开，主题提供 Light / Dark / System 三项。
移动 drawer 顶部显示带 `/` 提示的完整搜索框，右侧保留关闭按钮。

顶栏仍是全宽元素，但左侧被不透明侧栏覆盖，视觉上等同于顶栏从侧栏右缘
开始。移动端继续使用右侧 drawer，不改变顶栏触发方式。

右侧 TOC 的首行使用和正文上下文行相同的顶部间距 token，使
“On this page”与 breadcrumb / page actions 处于同一视觉基线。

左右栏折叠后的恢复按钮也使用该 token，与 breadcrumb / RSS-copy 工具行
对齐。自动隐藏顶栏只用原高度上方 60% 作为唤醒带，并在左右各留 64px
非激活角区，避免恢复按钮被误触发的顶栏盖住；整个 `< 768px` drawer 档位不
启用自动隐藏，并覆盖键盘专注模式的隐藏规则，顶栏始终可见。该档位右侧只保留
搜索与 drawer/menu 打开按钮。

### 1.2 栏目切换器

入口集合按以下顺序构造并去重：

1. `Site.Home.Sections.ByWeight` 的所有顶级栏目；
2. 全站所有 `sidebar_root_for: self` 的 Section，按页面权重顺序；
3. 当前解析出的 sidebar root（若前两组未包含它）。

顶级栏目可用 `sidebar_root_menu: false` 明确退出该集合。当前入口由
`shell/sidebar-root.html` 唯一解析，根菜单、侧栏树和 pager 不允许各自
发明另一套 root 规则。

- 0 个入口：不渲染；
- 1 个入口：无边框、无背景的可点击链接；
- 2 个及以上：渲染 dropdown，当前项有选中标记。

### 1.3 根文档必须进入阅读序列

侧栏树不得因为显示了栏目切换器而删掉根页面。每个 root 的可见序列必须是：

`root → first child → ... → last descendant`

因此：

- W/S 从正文进入树时，可落在 root，并能上下移动；
- Q/E 以同一可见树序翻页；
- root 没有 previous，末页没有 next；
- 当前页的 active/canonical 匹配必须能识别 root URL。

`sidebar_root_for: self` 的根行默认链接自身；仅当站点显式设置
`sidebar_root_link_self: false` 时，才保留旧版返回父栏目的兼容行为。

### 1.4 Taxonomy 顶栏菜单

当一级菜单指向 Hugo taxonomy 页（例如 `/tags/`）时，即使没有人工配置
children，也把它视为一个可展开菜单。面板内容为标签 chip：

- 数据源：对应 taxonomy 的 `.ByCount`；
- 主排序：数量降序；同数沿用 Hugo 的稳定名称序；
- 每个 chip 只有标签名和数量；
- 自适应规整网格，长标签允许省略，不输出完整层级列表；
- 一级标题仍是可点击链接，hover/focus 打开面板。

---

## 2. 文末组件

唯一顺序：

1. **Feedback**
2. **Annotation**
3. **Pager**（Previous / Next navigation）
4. **Comments**

所有 Docs、Book、Swagger 和 Blog 内容模板必须调用统一 `page-end.html`，
不得各自复制顺序。

### 2.1 默认值与覆盖

| 组件 | 主题默认 | 页面覆盖 |
| --- | --- | --- |
| Annotation | 开 | `annotation: false` |
| Feedback | 关 | `feedback: true/false` |
| Pager | Docs / Book / Blog 开 | `pager: false` 可单页退出 |
| Comments | 配置完整的 provider 可开；样例 Docs / Blog 开 | `comments: true/false` |

Feedback 不依赖 endpoint。站点已有 `gtag` 时记录结构化事件；没有 analytics
时 UI 仍正常工作并只在本地保存选择，不制造失败态。

### 2.2 Feedback

紧凑态为一行问题与两个 pill：Yes / No。点击任一项立即完成反馈：

1. 被选项显示 `aria-pressed=true`，并按页面与语言写入 `localStorage`；
2. 若存在全局 `gtag`，立即发送 `docs_feedback`，字段为 `result`、
   `page_path`、`language`；
3. No 可展开四个可选原因：缺少信息、错误或过时、步骤无效、难以理解；
4. 选择原因时再次发送 `docs_feedback`，附带 `reason` 与
   `refinement: true`，便于和首次计数区分；
5. 用户可清除本地选择并重新反馈；
6. UI 没有 textarea、Submit、登录流程或网络失败态。

主题默认关闭 Feedback；推荐只在 Docs、Book、Swagger 的 section cascade
开启，Blog 通常只保留评论。`params.ui.feedback.reasons: false` 可隐藏可选原因。

### 2.3 Feedback 与 Giscus 的边界

Giscus 仍是同一仓库的评论 iframe；用户在 iframe 内通过 GitHub OAuth 授权
giscus 代表自己发布。Feedback 不尝试写入 Giscus，也不创建 GitHub App robot。
当本页 Giscus 配置完整并启用时，反馈结果提供 “Add details in the comments”
锚点，滚动到本页评论区；两套数据流彼此独立。

### 2.4 Annotation

Annotation 是一个独立、可覆盖的 Hugo partial：

`layouts/_partials/page-annotation.html`

默认实现继续调用兼容 partial `page-meta-lastmod.html`，显示 last modified 与
commit，并兼容既有 `upstream_attribution` / `downstream_modified`。站点可直接
覆盖 `page-annotation.html`，读取任意 front matter，例如：

```yaml
upstream:
  project: minio/docs
  url: https://github.com/minio/docs
  license: CC BY 4.0
modified_by: Silo project
translated_from:
  language: English
  revision: 9d02de5
```

主题不规定这些扩展字段的 schema；它只保证稳定 slot 与组件顺序。

### 2.5 Pager

每张卡只有两个逻辑行：

1. 标题 + 方向箭头；Previous 左对齐，Next 右对齐；
2. 页面 description（缺失时使用纯文本 summary），Previous 左对齐，Next 右对齐。

只有一个方向时，该卡横跨整个容器；不能留下空半栏。

---

## 3. 全局快捷键修订

PRD 6 的 `l` 语言切换新增等价别名 `y`：

- 全部交互式页面生效；
- 两者调用同一个 `cycleLanguage()`；
- 输入框、contenteditable、IME、修饰键和打开的 dialog 仍优先；
- 单语言站静默 no-op。

首页同时把 `n` 作为“下一顶层 section”的助记别名，等同首页的 `j`；`k`
仍向上一节。该别名不进入 Docs / Blog 内页，避免占用新的全局按键。

根页面进入侧栏 DOM 后，现有 `visibleTreeLinks()` 即自然把它纳入 W/S 与
Q/E；不在 JavaScript 中注入一个不可见的特殊 root。

---

## 4. 样例站策略

`oink.pgsty.com` 的 Docs / Blog EN/ZH section cascade：

- `navbar_autohide: true`；
- `footer_style: slim`；
- `comments: true`（复用站点已配置的 Giscus）；
- `feedback: true`（仅 Docs cascade；Blog 继续只用 Giscus）。

本地 Hugo 成功、主题发布、analytics 收数与线上 Pages 生效必须分别验收。

---

## 5. 可访问性与安全红线

- 菜单和反馈按钮必须可通过键盘 focus 操作；菜单用 `aria-expanded`，反馈
  选项用 `aria-pressed`，异步状态用 `role=status`。
- 页面只有一个可见方向卡时仍保持正确 nav 语义。
- 减少动态偏好下禁用位移动画；forced-colors 下保留边界与焦点。
- Feedback 仅发送固定枚举、页面路径与语言，不采集或拼接自由文本。
- analytics 不可用、被拦截或抛错时不得阻断页面交互。
- 本地状态按语言与页面路径隔离，不在生成后的 HTML 中包含任何凭据。

---

## 6. 验收标准

1. Docs / Blog 桌面端左栏覆盖顶栏左侧；移动 drawer 无回归。侧栏搜索位于
   收起/关闭按钮左侧，底部语言、版本、主题、GitHub 工具坞在各宽度完整显示。
   左右恢复按钮与正文工具行对齐，顶栏只在上方 60% 中央区域唤醒且不覆盖
   两侧按钮；`< 768px` 时即使配置了 `navbar_autohide`，顶栏仍固定显示，右侧
   只保留搜索与 drawer/menu 打开按钮。
2. 根切换器默认列出所有顶级栏目和 self roots；单项为 ghost link。
3. Docs/Blog landing 的首个树链接是自身 root，W/S 可选，E 到第一篇，
   第一篇 Q 回 root。
4. `l`、`y` 在首页与所有内部页面调用相同语言路由，输入状态不触发；首页
   `n` 与 `j` 均前往下一顶层 section，`k` 返回上一节。
5. taxonomy 一级菜单和右栏均按 count 降序输出可自然换行的 tag/count cloud。
6. TOC 首行和 breadcrumb / page actions 上下文行顶部对齐；顶层分区隐藏重复的
   一级 breadcrumb，标题填入原 breadcrumb 空间，但 Action 下拉在根页与子页
   保持完全相同的位置。
7. 文末源码与渲染顺序均为 Feedback → Annotation → Pager → Comments。
8. 单方向 pager 占满宽度，卡片收窄为标题/简介两行；简介单行省略，Next 简介
   右对齐，Pager 与 Comments 之间不叠加大段留白。
9. Feedback 一次点击即记录；No 可选原因；状态按语言/页面持久化；
   Giscus 启用时可跳到评论区；页面中没有 textarea、Submit 或 endpoint。
10. Annotation 可通过 consumer layout 覆盖，旧的 lastmod override 继续工作。
11. Feedback 前端状态机通过 Node 测试，主题和样例 Hugo 构建通过；浏览器
   视觉回归作为独立人工验收层。
12. Markdown 表格恢复 table formatting context，至少填满正文宽度；表格容器
    自带下边距，后续正文不会紧贴表格。
