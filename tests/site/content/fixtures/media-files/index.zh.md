---
title: 媒体文件
description: 以 Markdown 图片语法书写的视频、音频与视频平台卡片的回归样例。
outputs: [HTML, print, markdown]
weight: 61
---

## 视频文件 {#video-file}

![两秒测试图案](https://example.org/media/demo.mp4)
{caption="带海报图和字幕的视频" poster="media/content-primitives-global.png" track="demo.vtt"}

![没有图注的视频](https://example.org/media/demo.mp4)

![循环演示](https://example.org/media/demo.mp4)
{autoplay=true caption="静音、循环、可见时播放"}

![带编号的视频](https://example.org/media/demo.mp4)
{num="7" caption="作为 Book 插图的视频"}

行内媒体是链接：句中的 ![测试图案](https://example.org/media/demo.mp4)。

## 音频文件 {#audio-file}

![两秒音调](https://example.org/media/clip.mp3)
{caption="440 Hz 正弦波"}

![第二个样本](https://example.org/media/clip.mp3)

> [!DETAILS]- 文字稿：第二个样本
>
> 与录音配套的一段简短文字稿。

行内音频是链接：句中的 ![音调](https://example.org/media/clip.mp3)。

## 平台卡片 {#platforms}

![OINK 架构分享](https://www.bilibili.com/video/BV1xx411c7mD?p=2&t=42)
{poster="media/content-primitives-global.png" caption="带海报图的 Bilibili 卡片"}

![YouTube 主题演讲](https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1m30s)

![Vimeo 短片](https://vimeo.com/76979871)
{width="4" height="3"}
