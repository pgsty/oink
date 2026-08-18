---
title: Content primitives
description: Regression fixtures for inline everyday content primitives.
outputs: [HTML, markdown]
weight: 30
lastmod: 2026-08-18
---

Status {{< badge text="Beta" tone="warning" >}} remains inline with prose.

Linked release {{< badge text="v0.3" tone="info" link="/release/" >}} and a
filled state {{< badge text="Deprecated" tone="danger" >}}.

Escaped text {{< badge text="R&D <Preview>" tone="success" >}} and long text
{{< badge text="A-deliberately-long-unbroken-status-value-for-responsive-layout" >}}.

CJK {{< badge text="实验功能" tone="info" >}} and RTL text
{{< badge text="ميزة تجريبية" tone="warning" >}}.

Open search with {{< kbd "Ctrl" "K" >}} or the command palette with
{{< kbd "⌘" "Shift" "P" >}}.

Escaped keys remain readable: {{< kbd "[" "A+B" ">" >}}.

## Fields

{{< fields label="Configuration fields" >}}
  {{< field name="offline_search" type="boolean" default=true required=true >}}
  Enables the local search index and links to the [documentation](/docs/).
  {{< /field >}}

  {{< field name="offline_search_max_results" type="integer" default=10 >}}
  Maximum number of visible results.

  A second paragraph preserves multiline description Markdown and `inline code`.
  {{< /field >}}

  {{< field name="explicitFalse" type="boolean" default=false >}}
  Proves that an explicit false value is not treated as an absent default.
  {{< /field >}}

  {{< field name="zeroLimit" type="integer" default=0 >}}
  Proves that an explicit zero value remains visible.
  {{< /field >}}

  {{< field name="emptyPrefix" type="string" default="" >}}
  Proves that an explicit empty string remains distinct from no default.
  {{< /field >}}

  {{< field name="resolverOutput" type="Array<string> | map[string]any" >}}
  Exercises angle brackets, brackets, and a union in a type value.
  {{< /field >}}

  {{< field name="aDeliberatelyLongUnbrokenConfigurationFieldNameForResponsiveLayout" type="namespace.ReallyLongGenericType<FirstArgument,SecondArgument>" >}}
  A long field name and type must stay within the component at narrow widths.
  {{< /field >}}

  {{< field name="搜索模式" type="字符串" default="本地" required=true >}}
  控制搜索是在浏览器本地执行，还是交给远程服务。
  {{< /field >}}

  {{< field name="وضع_البحث" type="سلسلة" default="محلي" >}}
  يختبر النص من اليمين إلى اليسار داخل تعريف الحقل.
  {{< /field >}}
{{< /fields >}}

## Tables

Ordinary wide tables scroll inside a keyboard-focusable viewport instead of
widening the page.

| Component | HTML behavior | Print behavior | Markdown behavior | Runtime |
| --- | --- | --- | --- | --- |
| Table | Scrolls within its own region | Expands at full width | Retains source table | None |

The `full-width` modifier opts out of the prose measure while keeping the same
contained overflow policy.

| Surface | Width | Narrow viewport | Print |
| --- | ---: | --- | --- |
| Full table | 100% | Horizontal scroll | Complete table |
{.full-width}

## FileTree

```filetree {title="Site tree"}
- content/                     # 0755 docs-admin:writers · Site content & templates
  - _index.md                  # 0644 vonng:docs · Section landing page
  - docs/
    - [index.md](/docs/)
    - [configuration.md](/docs/configuration/)   # 0644 docs-admin · Runtime settings
    - level1/
      - level2/
        - level3/
          - level4/
            - level5/
              - level6/
                - level7/
                  - level8/
                    - deeply-nested.md
- static/                      # 0750 release-engineering:documentation · Generated assets
  - favicon.ico
- hugo.yaml                    # root:root 0644
```
