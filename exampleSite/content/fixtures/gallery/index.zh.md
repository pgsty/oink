---
title: 画廊
description: 静态优先的响应式图片画廊回归样例。
outputs: [HTML, markdown]
image_zoom: true
---

```gallery
![蓝金配色的本地仪表盘总览](page.png) # 带固有尺寸的本页资源。
![绿紫配色的全局仪表盘细节](media/content-primitives-global.png) # 一段刻意写长的说明：它必须在自己的卡片里换行，既不撑宽页面，也不遮住旁边那张图。
![竖长的静态 SVG 设置界面](/media/content-primitives-tall.svg) # واجهة إعدادات عربية طويلة لاختبار الالتفاف والاتجاه التلقائي
![远端的部署历史视图](https://example.invalid/gallery/remote.webp?view=full) # 远程图片保持静态 URL，构建过程不会下载它。 {link=/zh/fixtures/gallery/}
```
