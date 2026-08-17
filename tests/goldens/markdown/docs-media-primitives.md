# Media primitives
> Regression fixtures for shared image resolution and the processed image shortcode.
---
LLMS index: [llms.txt](/llms.txt)
---
## Named page resource
![Blue and gold page-resource test pattern](page.png)
{command="Fit" options="48x32" caption="A page resource caption with inline code."}
## Named global resource
![Green and violet global-resource test pattern](media/content-primitives-global.png)
{command="Resize" options="32x" caption="A global asset caption."}
## Explicit decorative image
![](page.png)
{command="Crop" options="24x24"}
## Resource metadata alt and byline
![](page.png)
{command="Fill" options="40x24" caption="Alt text and the byline come from the resource metadata."}
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
