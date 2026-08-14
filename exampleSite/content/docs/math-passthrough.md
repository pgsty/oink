---
title: Math passthrough
description: Regression fixtures for delimiter-style server-rendered mathematics.
weight: 25
outputs: [HTML, markdown]
---

Inline passthrough renders \(E = mc^2\) without a browser-side math runtime.

The block form uses the same local server-side renderer:

$$
\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}
$$

The bracket form renders too:

\[\sum_{i=1}^{n} i = \frac{n(n+1)}{2}\]

When a consuming site cannot enable Goldmark passthrough, the parameter-free
`eq` shortcode is the explicit display-math escape hatch:

{{< eq >}}\lim_{n \to \infty}\left(1 + \frac{1}{n}\right)^n = e{{< /eq >}}

This deliberately long expression must scroll inside a narrow document column
instead of widening the page:

$$
\prod_{k=1}^{n}\left(1 + \frac{x_k^2}{1 + x_k^2}\right) + \sum_{j=1}^{m}\frac{a_j b_j c_j d_j}{\sqrt{1 + a_j^2 + b_j^2 + c_j^2 + d_j^2}} = \frac{\alpha + \beta + \gamma + \delta + \varepsilon}{\zeta + \eta + \theta + \iota + \kappa}
$$
