---
title: Media embeds
description: Regression fixtures for the asciinema, redoc, and swagger output states — interactive HTML, static print, and pure Markdown/RSS.
outputs: [HTML, print, markdown]
weight: 32
---

## Terminal recording

{{< asciinema file="images/install.cast" title="Install walkthrough" speed="2" startAt="60" rows="16" markers="10:Boot,25:Configure" >}}

## ReDoc reader

{{< redoc "openapi/sample.yaml" >}}

## Swagger explorer

{{< swagger src="/openapi/sample.yaml" >}}
