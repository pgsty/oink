# Media primitives
> Regression fixtures for shared image resolution and the processed image shortcode.
---
LLMS index: [llms.txt](/llms.txt)
---
## Named page resource
![Blue and gold page\-resource test pattern](/docs/media-primitives/page_hu_<hash>.png)
A **page resource** caption with `inline code`.
_OINK fixture byline_
## Named global resource
![Green and violet global\-resource test pattern](/media/content-primitives-global_hu_<hash>.png)
A global asset caption.
## Explicit decorative image
![](/docs/media-primitives/page_hu_<hash>.png)
_OINK fixture byline_
## Resource metadata alt and byline
![Page resource metadata alternative](/docs/media-primitives/page_hu_<hash>.png)
The **caption** is Markdown; alt text and the byline come from the resource metadata.
_OINK fixture byline_
## Plain Markdown image (render hook)
![Blue and gold page-resource test pattern](page.png "Advisory title")
![Static preview](/media/content-primitives-static.svg)
{caption="A static image with a caption becomes a figure"}
## Linked figure {#linked-figure}
![Blue and gold page-resource test pattern](page.png)
{caption="A linked figure keeps the anchor inside the figure" link="/docs/"}
## Processed native image {#processed-native}
![Blue and gold page-resource test pattern](page.png)
{command="Fit" options="32x20" caption="The attribute line can process too"}
