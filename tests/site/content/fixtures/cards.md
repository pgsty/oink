---
title: Cards (rich)
linkTitle: Cards (rich)
description: The `{{</* cards */>}}` / `{{</* card */>}}` full form with icons, badges, images and Markdown bodies.
outputs: [HTML, markdown]
weight: 35
---

{{< cards >}}
{{< card title="Install" link="/docs/" icon="fa-solid fa-rocket" badge="New" >}}
Deploy from scratch, *with Markdown* in the description.
{{< /card >}}
{{< card title="Configure" link="/fixtures/content-primitives/" icon="fa-solid fa-sliders" >}}
Tune runtime parameters.

A second paragraph.
{{< /card >}}
{{< card title="Reference" icon="fa-brands fa-github" >}}
A card without a link.
{{< /card >}}
{{< card title="With image" link="/fixtures/gallery/" image="/media/content-primitives-global.png" image_alt="Green and violet preview" >}}
Image cards resolve through the shared image resolver.
{{< /card >}}
{{< /cards >}}
