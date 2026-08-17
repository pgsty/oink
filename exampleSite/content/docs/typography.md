---
title: Typography fixture
description: Representative prose, labels, and code for theme regression checks.
weight: 10
---

OINK keeps interface text, article prose, headings, labels, and code in separate
typography roles. 中文正文用于验证明确的 CJK 回退与换行行为。

## Configure the theme

Inline `code` and the following block exercise Bootstrap's monospace bridge:

```yaml
params:
  ui:
    typography: technical
```

### Build the site

Run Hugo Extended without a frontend package manager.

### Inspect the result

Check the documentation shell, print view, and locally hosted fonts.

| Role | Purpose |
| --- | --- |
| UI | Navigation and controls |
| Body | Long-form documentation prose |
| Mono | Code and terminal output |

> Typography presets change font roles without changing the page structure.
