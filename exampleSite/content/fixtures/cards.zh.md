---
title: 卡片（完整形态）
linkTitle: 卡片（完整形态）
description: 带图标、徽章、图片与 Markdown 正文的 `{{</* cards */>}}` / `{{</* card */>}}` 完整形态。
outputs: [HTML, markdown]
weight: 35
---

{{< cards >}}
{{< card title="安装" link="/zh/docs/" icon="fa-solid fa-rocket" badge="新" >}}
从零开始部署，描述里*可以写 Markdown*。
{{< /card >}}
{{< card title="配置" link="/zh/fixtures/content-primitives/" icon="fa-solid fa-sliders" >}}
调整运行时参数。

第二个段落。
{{< /card >}}
{{< card title="参考" icon="fa-brands fa-github" >}}
一张没有链接的卡片。
{{< /card >}}
{{< card title="带图片" link="/zh/fixtures/gallery/" image="/media/content-primitives-global.png" image_alt="绿紫配色的预览图" >}}
带图片的卡片走共享的图片解析器。
{{< /card >}}
{{< /cards >}}
