---
title: 媒体组件
description: 共享图片解析与处理型图片的回归样例。
outputs: [HTML, markdown]
weight: 31
resources:
  - src: page.png
    params:
      alt: 来自资源元数据的替代文字
      byline: OINK 样例署名
---

## 具名页面资源

![蓝金配色的页面资源测试图](page.png)
{command="Fit" options="48x32" caption="一段带行内代码的页面资源图注。"}

## 具名全局资源

![绿紫配色的全局资源测试图](media/content-primitives-global.png)
{command="Resize" options="32x" caption="一段全局资源的图注。"}

## 显式的装饰图

![](page.png)
{command="Crop" options="24x24"}

## 资源元数据里的替代文字与署名

![](page.png)
{command="Fill" options="40x24" caption="替代文字与署名都来自资源元数据。"}

## 普通 Markdown 图片（渲染钩子）

![蓝金配色的页面资源测试图](page.png "悬停提示")

![静态预览图](/media/content-primitives-static.svg)
{caption="带图注的静态图片会变成 figure"}


## 带链接的 figure {#linked-figure}

![蓝金配色的页面资源测试图](page.png)
{caption="带链接的 figure 把锚点留在 figure 内部" link="/zh/docs/"}

## 处理型的原生图片 {#processed-native}

![蓝金配色的页面资源测试图](page.png)
{command="Fit" options="32x20" caption="属性行同样可以做图片处理"}
