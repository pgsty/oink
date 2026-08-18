---
title: Image Zoom
description: Regression fixtures for opt-in native image preview.
outputs: [HTML, markdown]
weight: 32
---

## Standalone Markdown image

![Blue and gold standalone preview](/media/content-primitives-static.svg)

## Processed image with a long caption

![Green and violet processed preview](media/content-primitives-global.png)
{command="Resize" options="56x" caption="This intentionally long caption verifies that the shared preview remains readable on narrow screens, preserves its accessible image name, and wraps without introducing page-level horizontal overflow."}

## Processed image with a caption but decorative alt

![](legacy-empty.png)
{command="Fit" options="48x32" caption="A decorative processed image is excluded from Zoom while its caption still supplies visible context."}

## Linked image exclusion

[![Linked image remains a link](/media/content-primitives-static.svg)](/docs/)
