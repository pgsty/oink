---
title: Attribute escaping
linkTitle: Attribute escaping
description: Generic data-* values that try to close their own attribute, on every render hook that emits them.
outputs: [HTML, markdown]
weight: 95
---

Every value below carries a double quote followed by an event handler. The
shared emitter (`content/attrs.html`) has to escape the quote, or the parser
ends the attribute there and reads the rest as real attributes -- which is how
an `onclick` once slipped past the policy that had just refused `on*`.

`check-output-security.py` fails the build on any inline event handler in the
output, so this page is what keeps that check honest: nothing else in the
example or fixture content emits a generic attribute value with a quote in it.

Each block also carries a class, so a regression cannot hide behind an
attribute block that was never parsed in the first place.

## Heading

### Heading with a hostile data value
{#attr-escape-heading .attr-escape data-probe="q\" onmouseover=alert(1) data-z=\"q"}

## Callout

> [!NOTE]
> The callout wrapper carries the value.
{.attr-escape data-probe="q\" onmouseover=alert(2) data-z=\"q"}

## Table

| Column | Value |
| --- | --- |
| First | 1 |
{.attr-escape data-probe="q\" onmouseover=alert(3) data-z=\"q"}

## Image

![Blue and gold standalone preview](/media/content-primitives-global.png)
{.attr-escape data-probe="q\" onmouseover=alert(4) data-z=\"q"}
