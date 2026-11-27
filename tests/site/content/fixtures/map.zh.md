---
title: 地图
description: map 数据围栏的回归样例：地点列表、已配置站点上的交互地图、路线与单个地点。
outputs: [HTML, print, markdown]
weight: 63
---

## 带路线的地点 {#route}

```map {caption="京都三日" route=true}
- name: 金阁寺
  lat: 35.0394
  lng: 135.7292
  text: 刚开门时最安静。
  image: media/content-primitives-global.png
  link: "#single"
- name: 清水寺
  lat: 34.9949
  lng: 135.785
- name: 伏见稻荷大社
  lat: 34.9671
  lng: 135.7727
  text: 千本鸟居要走两个小时。
```

## 单个地点 {#single}

```map {zoom=15 height="18rem"}
[{"name": "东京站", "lat": 35.6812, "lng": 139.7671}]
```
