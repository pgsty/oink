---
title: Media files
description: Regression fixtures for video and audio written as Markdown images, and video-platform cards.
outputs: [HTML, print, markdown]
weight: 61
---

## Video file {#video-file}

![A two-second test pattern](https://example.org/media/demo.mp4)
{caption="A captioned video with a poster and subtitles" poster="media/content-primitives-global.png" track="demo.vtt"}

![An uncaptioned video](https://example.org/media/demo.mp4)

![A looping demo](https://example.org/media/demo.mp4)
{autoplay=true caption="Muted, looped, plays while visible"}

![A numbered video](https://example.org/media/demo.mp4)
{num="7" caption="A Book figure that is a video"}

Inline media is a link: ![the test pattern](https://example.org/media/demo.mp4) in a sentence.

## Audio file {#audio-file}

![A two-second tone](https://example.org/media/clip.mp3)
{caption="440 Hz sine wave"}

![A second sample](https://example.org/media/clip.mp3)

> [!DETAILS]- Transcript: A second sample
>
> A short spoken line rendered alongside the recording.

Inline audio is a link: ![the tone](https://example.org/media/clip.mp3) in a sentence.

## Platform cards {#platforms}

![OINK architecture talk](https://www.bilibili.com/video/BV1xx411c7mD?p=2&t=42)
{poster="media/content-primitives-global.png" caption="A Bilibili card with a poster"}

![A YouTube keynote](https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1m30s)

![A Vimeo short](https://vimeo.com/76979871)
{width="4" height="3"}
