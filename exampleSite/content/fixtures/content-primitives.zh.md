---
title: 内容组件
description: 日常行内内容组件的回归样例。
outputs: [HTML, markdown]
weight: 30
---

状态 {{< badge text="Beta" tone="warning" >}} 与正文保持在同一行。

带链接的版本 {{< badge text="v0.3" tone="info" link="/release/" >}} 与一个
实心状态 {{< badge text="Deprecated" tone="danger" >}}。

转义文本 {{< badge text="R&D <Preview>" tone="success" >}} 与超长文本
{{< badge text="A-deliberately-long-unbroken-status-value-for-responsive-layout" >}}。

中文 {{< badge text="实验功能" tone="info" >}} 与从右向左的文字
{{< badge text="ميزة تجريبية" tone="warning" >}}。

用 {{< kbd "Ctrl" "K" >}} 打开搜索，用 {{< kbd "⌘" "Shift" "P" >}} 打开命令面板。

转义后的按键仍然可读：{{< kbd "[" "A+B" ">" >}}。

## 参数表

{{< fields label="配置项" >}}
  {{< field name="offline_search" type="boolean" default=true required=true >}}
  启用本地搜索索引，并链接到[文档](/zh/docs/)。
  {{< /field >}}

  {{< field name="offline_search_max_results" type="integer" default=10 >}}
  可见结果的最大条数。

  第二段用来验证多段说明里的 Markdown 与 `行内代码` 都被保留。
  {{< /field >}}

  {{< field name="explicitFalse" type="boolean" default=false >}}
  验证显式写出的 false 不会被当成「没有默认值」。
  {{< /field >}}

  {{< field name="zeroLimit" type="integer" default=0 >}}
  验证显式写出的 0 仍然可见。
  {{< /field >}}

  {{< field name="emptyPrefix" type="string" default="" >}}
  验证显式的空字符串与「没有默认值」不同。
  {{< /field >}}

  {{< field name="resolverOutput" type="Array<string> | map[string]any" >}}
  演练类型值里的尖括号、方括号与联合类型。
  {{< /field >}}

  {{< field name="aDeliberatelyLongUnbrokenConfigurationFieldNameForResponsiveLayout" type="namespace.ReallyLongGenericType<FirstArgument,SecondArgument>" >}}
  超长的字段名与类型在窄屏下也必须待在组件内部。
  {{< /field >}}

  {{< field name="搜索模式" type="字符串" default="本地" required=true >}}
  控制搜索是在浏览器本地执行，还是交给远程服务。
  {{< /field >}}

  {{< field name="وضع_البحث" type="سلسلة" default="محلي" >}}
  يختبر النص من اليمين إلى اليسار داخل تعريف الحقل.
  {{< /field >}}
{{< /fields >}}

## 表格

普通宽表格在一块可用键盘聚焦的区域内横向滚动，而不是把页面撑宽。

| 组件 | HTML 行为 | 打印行为 | Markdown 行为 | 运行时 |
| --- | --- | --- | --- | --- |
| 表格 | 在自己的区域内滚动 | 按整页宽度展开 | 保留源码表格 | 无 |

`full-width` 修饰让表格越出正文宽度，同时保持同样的溢出策略。

| 输出 | 宽度 | 窄视口 | 打印 |
| --- | ---: | --- | --- |
| 通栏表格 | 100% | 横向滚动 | 完整表格 |
{.full-width}

## 文件树

```filetree {title="站点目录树"}
- content/                     # 0755 docs-admin:writers · 站点内容与模板
  - _index.md                  # 0644 vonng:docs · 栏目首页
  - docs/
    - [index.md](/zh/docs/)
    - [configuration.md](/zh/docs/configuration/)   # 0644 docs-admin · 运行时设置
    - level1/
      - level2/
        - level3/
          - level4/
            - level5/
              - level6/
                - level7/
                  - level8/
                    - deeply-nested.md
- static/                      # 0750 release-engineering:documentation · 构建产物
  - favicon.ico
- hugo.yaml                    # root:root 0644
```
