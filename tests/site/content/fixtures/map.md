---
title: Maps
description: Regression fixtures for the map data fence — the place list, an interactive map on a configured site, a route, and a single place.
outputs: [HTML, print, markdown]
weight: 63
---

## Places with a route {#route}

```map {caption="Kyoto in three days" route=true}
- name: Kinkaku-ji
  lat: 35.0394
  lng: 135.7292
  text: Quietest right after opening.
  image: media/content-primitives-global.png
  link: "#single"
- name: Kiyomizu-dera
  lat: 34.9949
  lng: 135.785
- name: Fushimi Inari
  lat: 34.9671
  lng: 135.7727
  text: The gates climb for two hours.
```

## A single place {#single}

```map {zoom=15 height="18rem"}
[{"name": "Tokyo Station", "lat": 35.6812, "lng": 139.7671}]
```
