# PRD 7 Shell 与文末组件迁移指南

本指南覆盖 OINK 0.4.1 之后的导航、响应式 Shell、本地搜索预览与文末组件
变更。兼容性下限仍为 Hugo Extended 0.160.1。

[English](prd7-migration-guide.md)

## 1. 升级配置

OINK Feedback 现在是一次点击即可完成的结构化前端交互。请删除旧版或原型
配置中的 `yes`、`no`、`max_value`、`endpoint` 与 `max_length`；标准流程不需要
Worker，也不提交表单到后端 endpoint。

```yaml
params:
  offlineSearch: true
  # 大站本地预览默认不生成索引；仅在测试搜索时开启。
  offlineSearchOnServe: false
  ui:
    navbar_autohide: false
    annotation:
      enable: true
    pager:
      types: [docs, book, blog]
    feedback:
      enable: false
      reasons: true
    sidebar_root_menu: true
```

建议通过栏目 cascade 只在文档中开启反馈，Blog 继续只使用评论：

```yaml
# content/docs/_index.md
cascade:
  type: docs
  feedback: true
  comments: true
  navbar_autohide: true
  footer_style: slim
```

```yaml
# content/blog/_index.md
cascade:
  type: blog
  feedback: false
  comments: true
  navbar_autohide: true
  footer_style: slim
```

页面级 `feedback`、`annotation`、`comments` 与 `navbar_autohide` 会覆盖继承
策略，并且必须是布尔值。Pager 继续遵循 PRD 5 的既有约定：
`params.ui.pager.types` 决定在哪些内容类型中启用，页面或 cascade 中的
`pager: false` 用于单独退出。`params.ui.feedback.reasons: false` 只隐藏可选
原因，不影响两个主选项。

## 2. Analytics 与评论彼此独立

页面存在全局 `gtag` 时，主选项发送：

```text
docs_feedback { result, page_path, language }
```

可选原因再发送一条带 `reason` 和 `refinement: true` 的事件。没有 Analytics
时，UI 仍正常完成，并在本地记住固定枚举选择。OINK 不发送自由文本，也不会
为 Feedback 发起网络请求。

如果当前页已正确启用 Giscus，反馈结果会提供同页评论区锚点，供用户补充详情。
OINK 不会代替用户写入 Giscus、不创建 GitHub App 身份，也不把 Giscus iframe
当作表单 API。

## 3. 保留消费者覆盖

Docs、Book、Swagger 与 Blog 阅读模板统一调用
`layouts/_partials/page-end.html`，顺序为：

1. Feedback
2. Annotation
3. Previous/Next Pager
4. Comments

默认 Annotation 仍调用 `page-meta-lastmod.html`，因此既有消费者覆盖继续兼容。
需要来源、翻译版本或二次修改信息的站点可单独覆盖 `page-annotation.html`；不要
只为修改注释而复制整份内容模板。

Docs、Book 与 Blog Pager 统一遵循渲染后的侧栏顺序，并包含每个栏目根页面。
Blog 中显式设置 weight 的页面优先；未设置 weight 的页面按时间倒序排列。

## 4. 导航与响应式行为

`params.ui.sidebar_root_menu: true` 时，栏目切换器包含顶级栏目以及所有
`sidebar_root_for: self` 根栏目。顶级栏目可用 `sidebar_root_menu: false`
退出；当前根页面仍是侧栏与 Pager 的第一个可选入口。self-root 现在默认链接
自己的落地页；确实依赖旧版“返回父栏目”行为的站点，可以在该根栏目上显式设置
`sidebar_root_link_self: false` 保留旧行为。

一级菜单指向 Hugo taxonomy 页时（包括旧式 `/tags/` URL 菜单），桌面端显示
按数量排序的 term 面板；移动端只保留 taxonomy 父链接，不渲染完整标签云。

`params.ui.navbar_autohide: true` 只作用于 768px 及以上的精细指针视口；触屏
设备和整个 drawer 档位始终显示顶栏。移动 drawer 保留搜索、栏目切换、导航与
底部工具，快捷键帮助卡限制在 drawer 宽度内。

全局语言快捷键同时支持 `l` 与 `y`。首页中 `n` 与 `j` 前往下一个顶层
Landing section，`k` 返回上一节，`h` 切换专注模式。

## 5. 本地搜索预览

`hugo server` 默认不生成本地搜索索引。需要测试交互搜索时使用：

```sh
HUGO_PARAMS_OFFLINESEARCHONSERVE=true hugo server
```

只会归一化环境变量中精确的 `true` 与 `false` 字符串；其他非法值仍会让构建
失败。

## 6. 验证与发布边界

在主题仓库运行：

```sh
node --test 'tests/js/**/*.test.js'
python3 scripts/check-prd7.py
cd exampleSite && hugo --printPathWarnings --panicOnWarning
```

还应分别检查英文、中文的 Docs/Blog 根页与内页，以及桌面、drawer 与窄手机
宽度。必须把本地构建/预览、主题 tag 与 CI 发布、消费者版本锁定、部署和线上
页面分别验收；其中一层通过不能证明其他层已经完成。
