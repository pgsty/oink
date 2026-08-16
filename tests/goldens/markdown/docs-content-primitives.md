# Content primitives
> Regression fixtures for inline everyday content primitives.
---
LLMS index: [llms.txt](/llms.txt)
---
Status **Beta** remains inline with prose.
Linked release [**v0\.3**](/release/) and a
filled state **Deprecated**.
Escaped text **R\&D \<Preview\>** and long text
**A\-deliberately\-long\-unbroken\-status\-value\-for\-responsive\-layout**.
CJK **实验功能** and RTL text
**ميزة تجريبية**.
Open search with Ctrl + K or the command palette with
⌘ + Shift + P.
Escaped keys remain readable: \[ + A\+B + \>.
## Fields
**Configuration fields**
- `offlineSearch` — `boolean`; required; default: `true`
Enables the local search index and links to the [documentation](/docs/).
- `offlineSearchMaxResults` — `integer`; default: `10`
Maximum number of visible results.
A second paragraph preserves multiline description Markdown and `inline code`.
- `explicitFalse` — `boolean`; default: `false`
Proves that an explicit false value is not treated as an absent default.
- `zeroLimit` — `integer`; default: `0`
Proves that an explicit zero value remains visible.
- `emptyPrefix` — `string`; default: `""`
Proves that an explicit empty string remains distinct from no default.
- `resolverOutput` — `Array<string> | map[string]any`
Exercises angle brackets, brackets, and a union in a type value.
- `aDeliberatelyLongUnbrokenConfigurationFieldNameForResponsiveLayout` — `namespace.ReallyLongGenericType<FirstArgument,SecondArgument>`
A long field name and type must stay within the component at narrow widths.
- `搜索模式` — `字符串`; required; default: `本地`
控制搜索是在浏览器本地执行，还是交给远程服务。
- `وضع_البحث` — `سلسلة`; default: `محلي`
يختبر النص من اليمين إلى اليسار داخل تعريف الحقل.
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
- content/ — 0755 docs-admin:writers · Site content & templates
- _index.md — 0644 vonng:docs · Section landing page
- docs/
- [index.md](/docs/)
- [configuration.md](/docs/configuration/) — 0644 docs-admin · Runtime settings
- level1/
- level2/
- level3/
- level4/
- level5/
- level6/
- level7/
- level8/
- deeply-nested.md
- static/ — 0750 release-engineering:documentation · Generated assets
- `favicon.ico`
- hugo.yaml — *root:root 0644*
{.filetree}
