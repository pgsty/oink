---
title: Media primitives
description: Regression fixtures for shared image resolution and the processed image shortcode.
outputs: [HTML, markdown]
weight: 31
resources:
  - src: page.png
    params:
      alt: Page resource metadata alternative
      byline: OINK fixture byline
---

## Named page resource

{{< image src="page.png" command="Fit" options="48x32" alt="Blue and gold page-resource test pattern" >}}
A **page resource** caption with `inline code`.
{{< /image >}}

## Named global resource

{{< image src="media/content-primitives-global.png" command="Resize" options="32x" alt="Green and violet global-resource test pattern" >}}
A global asset caption.
{{< /image >}}

## Explicit decorative image

{{< image src="page.png" command="Crop" options="24x24" decorative=true >}}{{< /image >}}

## Resource metadata alt and byline

{{< image src="page.png" command="Fill" options="40x24" >}}
The **caption** is Markdown; alt text and the byline come from the resource metadata.
{{< /image >}}

## Plain Markdown image (render hook)

![Blue and gold page-resource test pattern](page.png "Advisory title")

![Static preview](/media/content-primitives-static.svg)
{caption="A static image with a caption becomes a figure"}


## Linked figure {#linked-figure}

![Blue and gold page-resource test pattern](page.png)
{caption="A linked figure keeps the anchor inside the figure" link="/docs/"}
