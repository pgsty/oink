# 导航迁移与配置参考

版本归属：纳入 OINK 0.3.0

本文描述 [pgsty/oink#11](https://github.com/pgsty/oink/issues/11) 跟踪的实现，
不表示 OINK 最新标签已经包含这些功能。只有当主题改动合并、某个发布标签明确
包含它们、消费站固定到该标签，并且本文的线上验收门禁全部通过后，消费站才
可以宣称这些功能可用。

规范性的设计决策仍以
[机器可检查契约](navigation-contract.md)为准。

## 发布状态 {#release-status}

当前 checkout 中的实现归入 OINK 0.3.0。只有当公开标签能够解析，且消费站固定到
该标签或更新版本后，才可采用本文的配置。不要把示例复制到仍固定旧标签的生产
站点，并假定旧主题能够理解这些配置。

发布顺序如下：

1. 合并主题侧功能改动；
2. 通过最低与当前 Hugo 版本的 CI 矩阵；
3. 发布明确包含该导航特性集的主题标签；
4. 消费站更新并固定到该标签；
5. 通过消费站 CI 与线上冒烟测试；
6. 完成以上步骤后，才可将功能标记为正式可用。

## 权威数据边界 {#authority-boundaries}

导航特性只增加交互能力，不增加第二套信息架构。

| 关注点 | 权威来源 |
| --- | --- |
| 全局导航 | Hugo `menus.main` |
| 侧栏 | Hugo 内容树与现有文档导航 |
| 产品或内容域切换 | 现有 root switcher |
| 页面发现 | 按语言隔离的本地搜索索引 |
| 页面与 Palette 动作 | 共享的内部 action registry |

不要增加 `docs.json`、`navigation.yaml` 或第二棵菜单树。Quick links 和
Palette 的 root 顺序都来自同一个 Hugo Menu 投影。

## 迁移路径 {#migration-path}

平铺菜单无需迁移。若要主动采用分组菜单：

1. 先在分支上修改，并在包含该功能的 OINK 版本发布后固定该版本；
2. 使用 Hugo `parent` identifier 给 `menus.main` 增加一层 child；
3. 新站点显式选择侧栏图标策略；
4. 给代表性页面和 cascade 增加搜索元数据；
5. 只增加安全 URL 或内置 action ID 命令；
6. 同时构建 root 与 subpath 版本，并在部署前完成键盘和屏幕阅读器检查。

### 升级门禁 {#upgrade-gate}

OINK 支持 Hugo Extended 0.160.1 与 CI 当前版本。消费站升级前，发布版本必须
同时通过这两个版本。生产环境应在 `go.mod` 固定主题版本，不要把 `@latest`
当作发布策略。

### Root 与 Subpath 构建 {#root-and-subpath-builds}

站内菜单项使用 `pageRef`，Hugo 才能正确解析当前语言与 `baseURL`：

```sh
hugo --baseURL https://docs.example.com/
hugo --baseURL https://example.com/preview/
```

第二个构建中，站点拥有的内部 navbar、root switcher、搜索索引、页面动作、
命令、语言与版本 URL 都必须位于 `/preview/` 下。外部 edit、issue、GitHub、
root/version 与自定义命令目标保持不变。不要在消费站 override 中硬编码域名
根路径。

## 嵌套导航 {#nested-navigation}

只有一层 child 具备交互行为。Parent label 仍然是普通链接，相邻按钮只负责
打开或关闭 dropdown/accordion。

```yaml
menus:
  main:
    - identifier: docs
      name: 文档
      pageRef: /docs
      weight: 10
    - identifier: guides
      parent: docs
      name: 指南
      pageRef: /docs/tutorial
      weight: 10
      params:
        icon: fa-solid fa-route
        description: 面向任务的教程
    - identifier: reference
      parent: docs
      name: 参考
      pageRef: /docs/reference
      weight: 20
      params:
        icon: fa-solid fa-book
        description: 配置与 API 参考
```

没有 children 的项继续走原有平铺链接路径。当 parent 自身或后代为当前页时，
parent 显示 active；只有精确匹配的页面才获得 `aria-current="page"`。

### 导航交互 {#navigation-interaction}

Parent 标签是普通链接：点击前往栏目落地页，hover 或键盘聚焦展开面板。
ArrowDown 打开并聚焦第一项，Escape 关闭并还焦，在外部按下指针时面板关闭。
到达子页面永远不依赖 hover。

导航栏只有两种状态——完整与紧缩。紧缩态的内容菜单项使用图标；小于 `md` 时，
右侧 utility 只保留搜索与对应的菜单或 drawer 打开按钮，语言、版本、主题和
GitHub 移入 drawer 底部。原 `navbar_accordion_single_open` accordion 参数已
退役并被忽略。

导航栏高度为 50px。设置 `params.ui.navbar_autohide: true` 后，在鼠标类精细
指针设备上，导航栏默认收起到视口上方；指针进入顶部原区域上方 60%，或键盘焦点
进入导航栏时，它会以浮层形式出现。纯触屏设备与小于 768px 的 drawer 档位始终
常显，后者也覆盖键盘阅读模式的隐藏规则。页面或栏目 cascade 可用
顶层 front matter `navbar_autohide` 覆盖全局策略；`navbar_enabled: false` 仍是
完全不渲染导航栏的独立选项。

语言、版本、主题和搜索仍位于 utility 区域，不会变成内容菜单的 children。

### 深层菜单降级 {#deep-menu-degradation}

超过支持 child 层级的条目会产生 Hugo build warning，并渲染为带链接的静态
group heading 与普通后代，不会生成第三级 flyout。这个 warning 提醒站点把
深层信息架构放回内容侧栏，不应被当作可以静默忽略的提示。

### 外部导航 {#external-navigation}

跨 host 条目带有外链视觉提示，并使用 `rel="noopener noreferrer"` 打开。
内部链接仍能感知语言和 subpath。Target 由主题解析，站点配置不能注入任意
链接执行行为。

## 侧栏图标策略 {#sidebar-icon-policy}

`params.ui.sidebar_icon_policy` 接受：

| 值 | 行为 |
| --- | --- |
| `all` | 每个符合条件的侧栏条目显示解析后的图标。 |
| `groups` | Root 和有 children 的节点显示图标；普通 leaf 不显示。 |
| `none` | 不输出侧栏条目图标。 |

在 1.0 之前，未配置时的兼容默认值仍为 `all`；新 starter site 也显式选择
`all`，确保叶子页面中已配置的图标不会被隐藏。偏好稀疏结构树的站点仍可主动
选择 `groups`。非法值会 warning 并回退到 `all`。

## 搜索元数据与索引 {#search-metadata-and-index}

本地搜索继续支持离线工作，并按语言隔离。Palette 扩展现有索引，不会用远程
服务替换它。

### 规范搜索字段 {#canonical-search-fields}

```yaml
---
title: PostgreSQL 配置
search_keywords: [postgres, postgresql, pg]
search_boost: 1.5
search_exclude: false
---
```

- `search_keywords` 接受单个字符串或数组，同时参与 Latin 和 CJK substring
  匹配。
- `search_boost` 必须是有限正数，默认 `1.0`。非法、零、负数、无穷大或非数字
  值会 warning 并使用 `1.0`。
- `search_exclude` 是规范排除字段。

`exclude_search` 与 `excludeSearch` 是 0.x 的兼容别名（0.4 起对新内容弃用），
1.0 已删除：页面若仍写任一别名，构建会失败并在错误信息中给出
`search_exclude`；换键名、值不变即可。

### Cascade 继承 {#cascade-inheritance}

使用 Hugo cascade 设置产品或 section 默认值，必要时再由页面覆盖：

```yaml
---
title: 文档
cascade:
  search_boost: 1.25
---
```

索引在 Hugo cascade 继承完成后解析 `search_boost`。页面值按照 Hugo 标准
front matter 规则覆盖继承值。

### 索引 Schema 与回退 {#index-schema-and-fallbacks}

每条记录保留 `ref`、`title`、`categories`、`tags`、`excerpt`，并增加以下
确定性元数据：

| 字段 | 值与回退 |
| --- | --- |
| `root` | 小写 `FirstSection`；没有 section 时为 `home`。 |
| `section` | 小写 `CurrentSection`；缺失时回退到 `root`。 |
| `type` | 小写 Hugo page type；缺失时回退到 `root`。 |
| `keywords` | 规范化的 `search_keywords` 数组；缺失时为空数组。 |
| `boost` | 有效的继承 multiplier；否则为 `1.0`。 |
| `breadcrumb` | 从 root 到当前页的本地化标题路径。 |
| `icon` | 依次使用页面、当前 section、root、稳定 type/root 回退。 |

`params.offline_search_index` 控制可选文本字段：

| Scope | 增加字段 |
| --- | --- |
| `title` | 不增加文本字段。 |
| `heading` | `headings` |
| `summary` | `headings`、`description` |
| `content` | `headings`、`description`、`body` |

`summary` 适合作为 starter 默认值。`content` 召回最广，但下载通常最大。每种
语言生成独立索引，绝不会回退到另一种语言的记录。

### 排序行为 {#ranking-behavior}

页面最终分数为 `text match score × search_boost`。Keywords 与 multiplier
同时应用于 Lunr 和确定性的 CJK substring 路径。稳定的 title/ref tie-break
避免排序随 locale 或浏览器变化。`params.offline_search_max_results` 只限制页面
命中；匹配的 Actions 独立分组，不占用页面配额。

### 索引大小预算 {#index-size-budget}

回归 fixture 对每种语言设置 2 MiB 未压缩、512 KiB gzip 上限。内容更多的
消费站必须测量自己的生成索引，并主动选择 `title`、`heading`、`summary` 或
`content`。Fixture budget 是发布门禁，不保证任意站点内容都不会超过它。

## Command Palette 与动作 {#command-palette-and-actions}

现有 Cmd/Ctrl-K 本地搜索 dialog 升级为 Command Palette，仍然只有一个 dialog
和一份本地索引。

### Palette 模式 {#palette-modes}

| 输入 | 结果 | 索引请求 |
| --- | --- | --- |
| 空查询 | Quick links、页面动作、偏好设置、自定义命令 | 无 |
| 普通文本 | 按 root 分组的页面与匹配 Actions | 延迟加载、同源 |
| 前缀 `>` | 仅内置与自定义命令 | 无 |

第一版不支持 `@docs` 与 `@blog` scope。索引失败不会移除命令，旧异步请求也
不能覆盖新的 Palette session。

### 内置 Action ID {#built-in-action-ids}

| ID | 类型 | 通常可用条件 |
| --- | --- | --- |
| `copy_markdown` | Invoke | 当前页存在 Markdown output。 |
| `open_chatgpt` | URL | `page_context_menu.assistant_links` 为 true；激活时使用当前浏览器 URL。 |
| `open_claude` | URL | `page_context_menu.assistant_links` 为 true；激活时使用当前浏览器 URL。 |
| `view_markdown` | URL | 当前页存在 Markdown output。 |
| `view_history` | URL | 能从 `github_repo` 解析仓库路径。 |
| `edit_page` | URL | 能解析仓库/edit URL。 |
| `create_issue` | URL | 已配置仓库。 |
| `print` | Invoke | 交互式 HTML output。 |
| `switch_theme` | Choice | 已启用主题切换。 |
| `switch_language` | Choice | 存在多于一个语言目标。 |
| `switch_version` | Choice | 存在版本条目。 |
| `open_github` | URL | 已配置项目仓库。 |

对应的页面与 Palette actions 共享 descriptor 和 URL 解析。“复制文本”
共享 pending/success cache；Print 调用共享 print executor；主题控件调用同一个
theme apply 函数。助手 actions 先提供无 JavaScript 可用的真实 fallback anchor，
激活时再从浏览器 URL 解析实际部署域名、查询参数与片段。其他内置 URL actions
的 href 与共享 descriptor 保持一致。页面侧的 actions 以文档标题旁的 split button
呈现——“复制文本”为主按钮，caret 展开完整菜单——取代早先的 TOC rail 列表。
内置集合之外的历史 rail-only actions 继续作为独立兼容功能，
现列于同一展开菜单中。

助手链接默认关闭，因为激活会把完整浏览器 URL 发送给第三方。站点选择启用时，
必须避免在 query string 与 fragment 中放置秘密信息、披露该出站边界，并可用布尔型
front matter 里同名键 `page_context_menu: { assistant_links: false }` 按页面收窄。

```yaml
params:
  ui:
    page_context_menu:
      assistant_links: true
```

如果站点已经全局启用，但某个页面包含敏感 URL，请在该页 front matter 中设置
`page_context_menu: { assistant_links: false }`，单独关闭助手入口（裸的
`page_context_menu: false` 会隐藏整个菜单）；站点未开启时页面无法自行开启。

### 自定义命令与本地化 {#custom-commands-and-localization}

在默认语言参数下定义完整记录，并用稳定 `id` 而不是数组位置进行翻译：

```yaml
languages:
  en:
    params:
      ui:
        command_palette:
          commands:
            - id: status
              title: Service status
              description: View uptime and incidents
              url: https://status.example.com/
              icon: fa-solid fa-signal
              keywords: [uptime, incident]
            - id: print_page
              title: Print this page
              action: print
              keywords: [paper, pdf]
  zh:
    params:
      ui:
        command_palette:
          commands:
            - id: print_page
              title: 打印此页
              keywords: [纸张, PDF]
            - id: status
              title: 服务状态
              keywords: [可用性, 故障]
```

当前语言按 ID 覆盖默认记录，缺失字段回退到默认语言。默认记录或仅在某 locale
新增的 ID 必须且只能定义一个 `url` 或一个允许的内置 `action` ID；已有 ID 的
本地化 override 可以同时省略两者并继承默认值。合并后的每条有效命令仍然必须
只有一种执行类型。

### 命令安全边界 {#command-security-boundary}

配置是 inert data，不能提供 callback、event handler、function name、JavaScript
源码或 executor。未知或保留 ID、重复 ID、不支持的 key、字段类型错误、同时
提供 `url` 与 `action`、未知内置 action 都会让 Hugo build 失败。

URL 只允许站内相对地址或显式 `http:`/`https:`。构建会拒绝 `javascript:`、
`data:`、`vbscript:`、`file:`、protocol-relative URL、反斜杠与控制字符；
runtime 还会再次校验。外部 URL 使用 `noopener noreferrer`。渲染只使用模板
转义文本或 DOM `textContent`，绝不会执行 manifest 数据。

## 键盘与屏幕阅读器 {#keyboard-and-screen-readers}

### Navbar 交互表 {#navbar-interaction-table}

| 上下文 | 按键或动作 | 结果 |
| --- | --- | --- |
| Parent link | Enter | 导航到 parent 页面。 |
| Disclosure button | Enter 或 Space | 切换面板。 |
| 桌面 disclosure | ArrowDown | 打开并聚焦第一项。 |
| 已打开桌面面板 | ArrowUp/Down、Home/End | 在可操作项之间移动。 |
| 已打开桌面面板 | Escape | 关闭并恢复 disclosure 焦点。 |
| 已打开桌面面板 | Tab 或外部按下 | 正常离开并关闭面板。 |
| 移动端 parent link | 激活 | 导航但不切换 accordion。 |
| 移动端 disclosure | 激活 | 切换但不导航。 |

Disclosure button 暴露 `aria-expanded` 与 `aria-controls`。面板使用 disclosure
pattern，而不是 ARIA application menu，因此 child links 保留原生链接语义。

### Palette 交互表 {#palette-interaction-table}

| 按键或动作 | 结果 |
| --- | --- |
| Cmd/Ctrl-K | 打开或关闭 Palette。 |
| 在可编辑控件外按 `/` | 直接以命令模式打开 Palette。 |
| ArrowUp/ArrowDown | 移动 active listbox option。 |
| Cmd/Ctrl-Home 或 Cmd/Ctrl-End | 移到第一项或最后一项。 |
| Enter | 只执行一次当前 option。 |
| Escape | 关闭并把焦点还给可见的调用控件。 |
| Tab/Shift-Tab | 焦点保持在 modal dialog 内。 |
| IME composition 按键 | 继续编辑输入法组合，不导航也不执行。 |

DOM focus 保持在可编辑 combobox 中，`aria-activedescendant` 指向 active listbox
option。结果 section 是带标签的 group。有原因的 disabled choice 可被发现但不
执行。Polite live region 宣布结果数、错误与动作结果，不会在每次箭头移动时重复
播报。Reduced-motion 用户无需等待关闭动画。移动端焦点会回到可见的 drawer/
menu opener，而不是已经隐藏在关闭 surface 内的控件。

## Runtime 与隐私保证 {#runtime-and-privacy-guarantees}

只有同时满足以下条件时才启用 Palette capability：

1. `params.offline_search` 为 true；
2. 页面是 home 或使用 shell surface；
3. 当前 output 不是 `print`。

禁用时，页面不会输出 Palette dialog markup、本地索引引用、Lunr、Palette result
model 与 Palette controller。Print output 同样省略这些 runtime。Action manifest
与共享页面动作 registry 可能仍存在，因为 progressive page actions 独立于搜索。

空查询与 `>` 模式不获取索引；普通文本只获取当前语言、同源生成的 JSON。
OINK 默认不发送 telemetry、query upload、analytics event、remote-search
request 或助手 URL。消费站显式启用的助手链接、analytics、评论、托管搜索或外部
命令 URL 属于另一项站点策略，必须由消费站自行披露。

## 兼容窗口 {#compatibility-window}

- 现有平铺 `menus.main` 无需改配置，HTML 与行为继续受到兼容测试保护。
- 整个 0.x 期间，未配置 `params.ui.sidebar_icon_policy` 时仍为 `all`；starter
  显式选择 `all`，确保已配置的叶子页图标保持可见。
- `exclude_search` 与 `excludeSearch` 在整个 0.x 期间保留；1.0 已删除，构建
  失败并提示替代键。
- Cmd/Ctrl-K 继续作为 Palette 快捷键，普通文本继续搜索页面。
- `/` 仅在焦点不位于 input、textarea、select 或 contenteditable 区域时打开命令模式。
- 迁移不会增加第二套导航权威源或默认网络服务。

任何别名删除或默认值变更都需要未来 major release 的迁移条目与更新后的
characterization fixtures。

## Starter 与主题默认值 {#starter-versus-theme-defaults}

最小 `exampleSite/hugo.yaml` 有意演示嵌套 Hugo Menu、
`sidebar_icon_policy: all`、summary 大小的本地搜索，以及安全 URL 与内置
命令。显式的 `all` 会保留叶子页中已配置的图标，并与主题兼容默认值一致；
`groups` 仍可作为稀疏模式主动启用。

## 验证与发布证据 {#verification-and-release-evidence}

### 本地验证门禁 {#local-verification-gates}

在所有支持的 Hugo 版本下运行主题专项检查：

```sh
python3 scripts/check-navigation-contract.py
python3 scripts/check-runtime-isolation.py
python3 scripts/check-sidebar-icons.py
python3 scripts/check-search.py
python3 scripts/check-actions.py
python3 scripts/check-palette.py
python3 scripts/check-navigation-docs.py
```

这些检查覆盖 root/subpath、EN/ZH、flat/nested/deep menu、search on/off、
home/docs/blog/plain/print surface、CJK 排序、registry 安全、Palette 状态与文档
等价性。消费站仍必须单独运行 Hugo、链接、翻译、Playwright 与 axe 测试。某一层
通过不能证明后续交付层也已通过。

### 证据台账 {#evidence-ledger}

| 门禁 | 当前证据 | 发布状态 |
| --- | --- | --- |
| 契约/runtime/导航/搜索/actions/Palette | [主题 #18](https://github.com/pgsty/oink/issues/18#issuecomment-5263306916) 与各 owning issue 的专项结果；发布候选需重跑 | 既往本地通过；当前候选必须重新通过 |
| 消费站 root/subpath、EN/ZH、浏览器与 axe | [消费站 #3 证据](https://github.com/pgsty/oink.pgsty.com/issues/3#issuecomment-5263727126)；发布候选需重跑 | 既往本地通过；当前候选必须重新通过 |
| 最低/当前 Hugo 矩阵 | [主题 CI workflow](../.github/workflows/ci.yml) | 必须在合并 commit 上通过 |
| 带标签主题产物 | 包含该功能的 release 页面与 checksum | 待完成 |
| 消费站版本固定与部署 | 消费站 commit 与 deployment run | 待完成 |
| 线上 root/subpath 冒烟 | 公网 URL、实际资源路径、键盘与 telemetry trace | 待完成 |

本地视觉检查、单元测试、集成测试、CI、package/tag 发布、消费站部署与线上可用性
是不同门禁。

### 发布检查清单 {#release-checklist}

- [ ] 主题 owning changes 已 review 并合并。
- [ ] Hugo 0.160.1 与当前版本 CI 在合并 commit 上为绿色。
- [ ] Changelog 与 tag 明确列出该导航功能集。
- [ ] 消费站固定包含该功能的 tag，而不是本地 replacement。
- [ ] 消费站非浏览器、浏览器与 axe 套件在 CI 中通过。
- [ ] Root 与 subpath 部署从正确前缀加载语言本地索引与内部 URL。
- [ ] Print 与禁用搜索页面不加载 Palette runtime。
- [ ] Network trace 确认没有默认 query 或 telemetry request。
- [ ] 线上键盘与屏幕阅读器冒烟通过。
- [ ] 只有前述门禁全部完成后，消费站才能向读者宣称这些功能可用。
