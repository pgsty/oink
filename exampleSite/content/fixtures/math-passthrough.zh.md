---
title: 公式 passthrough
description: 分隔符式、服务端渲染公式的回归样例。
weight: 25
outputs: [HTML, markdown]
---

行内 passthrough 渲染 \(E = mc^2\)，浏览器端没有数学运行时。

块级形式走的是同一个本地服务端渲染器：

$$
\int_{-\infty}^{\infty} e^{-x^2}\,dx = \sqrt{\pi}
$$

方括号形式同样可以：

\[\sum_{i=1}^{n} i = \frac{n(n+1)}{2}\]

消费站点无法开启 Goldmark passthrough 时，不带参数的 `eq` shortcode
就是块级公式的显式逃生口：

{{< eq >}}\lim_{n \to \infty}\left(1 + \frac{1}{n}\right)^n = e{{< /eq >}}

下面这个刻意写长的表达式必须在窄正文栏里横向滚动，而不是把页面撑宽：

$$
\prod_{k=1}^{n}\left(1 + \frac{x_k^2}{1 + x_k^2}\right) + \sum_{j=1}^{m}\frac{a_j b_j c_j d_j}{\sqrt{1 + a_j^2 + b_j^2 + c_j^2 + d_j^2}} = \frac{\alpha + \beta + \gamma + \delta + \varepsilon}{\zeta + \eta + \theta + \iota + \kappa}
$$
