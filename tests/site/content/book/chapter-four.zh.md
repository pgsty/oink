---
title: 公式与推导
description: 当论证由数学而不是由散文承担时，一章看起来是什么样子。
book_kind: chapter
book_number: 4
weight: 40
outputs: [HTML, print, markdown]
---

> *不必为你在数学上遇到的困难担心，我可以向你保证，我遇到的更大。*
>
> —— 阿尔伯特·爱因斯坦，致 Barbara Wilson 的信（1943）

前三章的论证由表格承担，这一章交给公式。这对排版提出了三个散文从不提出的要求：
行内公式要能嵌进句子而不撑高行距；行间公式要能编号、并且能被别的章节引用；
推导要能跨若干对齐的行展开，而不至于沦为一张图片。

用来演示的题目是反向传播——年代久远，短到可以完整写下，并且对记号毫不宽容。[^nielsen]

## 约定记号 {#notation}

后文用到的每个符号都先在一张表里出现一次，并写明它的形状。读者一旦搞不清 \(W\) 到底是
一个矩阵还是一列矩阵，这一章就读不下去了，再多的散文也补不回来。

| 名称 | 符号 | 形状 | 含义 |
| --- | :---: | :---: | --- |
| 输入 | \(x = a^{1}\) | \(d_1 \times 1\) | 输入层的激活值 |
| 权值 | \(W^{l}\) | \(d_l \times d_{l-1}\) | 第 \(l-1\) 层到第 \(l\) 层，每个神经元占一行 |
| 偏置 | \(b^{l}\) | \(d_l \times 1\) | 每个神经元一个标量 |
| 带权输入 | \(z^{l} = W^{l} a^{l-1} + b^{l}\) | \(d_l \times 1\) | 激活函数接收到的值 |
| 激活值 | \(a^{l} = \sigma(z^{l})\) | \(d_l \times 1\) | 本层输出的值 |
| 误差 | \(\delta^{l} \equiv \partial C / \partial z^{l}\) | \(d_l \times 1\) | 代价对带权输入的敏感度 [^whyz] |
{#tbl-notation num="4-1" caption="L 层网络的记号约定。层号从 1 开始，输入层没有自己的权值。"}

## 从一个神经元到一层 {#one-layer}

单个神经元先算加权和，再过一遍激活函数。把一层里的神经元写成同一个矩阵的各行，
\(d_l\) 个标量方程就压缩成了一个：

$$
\begin{bmatrix} a^{l}_{1} \\ \vdots \\ a^{l}_{d_l} \end{bmatrix}
= \sigma\!\left(
\begin{bmatrix}
  w^{l}_{1,1} & \cdots & w^{l}_{1,d_{l-1}} \\
  \vdots      & \ddots & \vdots \\
  w^{l}_{d_l,1} & \cdots & w^{l}_{d_l,d_{l-1}}
\end{bmatrix}
\begin{bmatrix} a^{l-1}_{1} \\ \vdots \\ a^{l-1}_{d_{l-1}} \end{bmatrix}
+
\begin{bmatrix} b^{l}_{1} \\ \vdots \\ b^{l}_{d_l} \end{bmatrix}
\right)
$$
{#eq-layer num="4.1" caption="一层的前馈计算：写一次，而不是每个神经元写一次。"}

激活函数几乎总是取 logistic sigmoid，看中的与其说是它的形状，不如说是下面第二行：
它的导数由前馈过程中已经算出来的值直接相乘得到。

$$
\begin{aligned}
\sigma(z) &= \frac{1}{1 + e^{-z}} \\[4pt]
\sigma'(z) &= \sigma(z)\bigl(1 - \sigma(z)\bigr) = a \odot (1 - a)
\end{aligned}
$$
{#eq-sigmoid num="4.2" caption="sigmoid 及其导数，⊙ 表示逐元素（Hadamard）乘积。"}

## 四个方程 {#four-equations}

反向传播就是四个方程：第一个给出输出层的误差，第二个把误差往前推一层，
后两个把某一层的误差换算成该层参数的梯度。

| 方程 | 需要什么 | 编号 |
| --- | --- | :---: |
| \(\delta^{L} = \nabla_a C \odot \sigma'(z^{L})\) | 网络输出 \(a^{L}\) 与标注 \(y\) | BP1 |
| \(\delta^{l} = \bigl(W^{l+1}\bigr)^{\mathsf{T}} \delta^{l+1} \odot \sigma'(z^{l})\) | 后一层的权值与误差 | BP2 |
| \(\nabla_{W^{l}} C = \delta^{l} \bigl(a^{l-1}\bigr)^{\mathsf{T}}\) | 本层误差与前一层输出 | BP3 |
| \(\nabla_{b^{l}} C = \delta^{l}\) | 只需要本层误差 | BP4 |
{#tbl-backprop num="4-2" caption="反向传播的四个方程。只有 BP2 是递推的，其余三个都是局部的。"}

取二次代价 \(C = \tfrac{1}{2}\lVert y - a^{L} \rVert^{2}\)、激活函数取 sigmoid 时，
BP1 与 BP2 会退化成只含前馈过程已保存量的表达式：

$$
\delta^{L} = (a^{L} - y) \odot (1 - a^{L}) \odot a^{L}
$$
{#eq-bp1 num="4.3" caption="二次代价 + sigmoid 下的 BP1：运行时不需要真的求一次导数。"}

## 证明误差传递方程 {#prove-bp2}

四个方程里只有 BP2 值得在这里证一遍，因为只有它能体现出：把 \(\delta\) 定义在 \(z\)
而不是 \(a\) 上，究竟换来了什么。从定义出发，引入后一层的带权输入作为中间变量，
再链式求导：

$$
\begin{aligned}
\delta^{l}_{j}
&= \frac{\partial C}{\partial z^{l}_{j}}
 = \sum_{k=1}^{d_{l+1}} \frac{\partial C}{\partial z^{l+1}_{k}} \frac{\partial z^{l+1}_{k}}{\partial z^{l}_{j}}
 = \sum_{k=1}^{d_{l+1}} \delta^{l+1}_{k} \frac{\partial z^{l+1}_{k}}{\partial z^{l}_{j}} \\[4pt]
z^{l+1}_{k}
&= \sum_{j=1}^{d_{l}} w^{l+1}_{kj}\, \sigma\bigl(z^{l}_{j}\bigr) + b^{l+1}_{k}
\quad \Longrightarrow \quad
\frac{\partial z^{l+1}_{k}}{\partial z^{l}_{j}} = w^{l+1}_{kj}\, \sigma'\bigl(z^{l}_{j}\bigr) \\[4pt]
\delta^{l}_{j}
&= \sigma'\bigl(z^{l}_{j}\bigr) \sum_{k=1}^{d_{l+1}} \delta^{l+1}_{k}\, w^{l+1}_{kj}
 = \sigma'\bigl(z^{l}_{j}\bigr) \Bigl[ \bigl(W^{l+1}\bigr)^{\mathsf{T}} \delta^{l+1} \Bigr]_{j}
\end{aligned}
$$

最后一行里的求和，是后一层误差向量与后一层权值矩阵第 \(j\) 列的点积。取那一列，
等价于取转置矩阵的第 \(j\) 行——{{< xref tbl="4-2" anchor="tbl-backprop" />}} 里那个
\(\mathsf{T}\) 就是这么来的：转置不是记号上的花哨，它就是这个方程的全部内容。

## 五十行代码 {#implementation}

四个方程翻译过来就是四行数组运算。一章既然把它们写了出来，就该把这个翻译也摆出来，
而不是只声称它成立。

```python {num="4-1" caption="按小批量做随机梯度下降，标注出来的四行分别是 BP1 到 BP4。" #eg-network}
import numpy as np

class Network:
    def __init__(self, sizes):
        self.L = len(sizes)
        self.layers = range(self.L - 1)
        self.w = [np.random.randn(y, x) for x, y in zip(sizes[:-1], sizes[1:])]
        self.b = [np.random.randn(x, 1) for x in sizes[1:]]

    def feed_forward(self, a):
        for l in self.layers:
            a = 1.0 / (1.0 + np.exp(-np.dot(self.w[l], a) - self.b[l]))
        return a

    def train(self, batch, eta):
        x, y = batch
        r, a = eta / x.shape[1], [x]
        for l in self.layers:                                    # 前馈
            a.append(1.0 / (1.0 + np.exp(-np.dot(self.w[l], a[-1]) - self.b[l])))

        d = (a[-1] - y) * a[-1] * (1 - a[-1])                    # BP1
        for l in range(1, self.L):
            if l > 1:
                d = np.dot(self.w[-l + 1].T, d) * a[-l] * (1 - a[-l])   # BP2
            self.w[-l] -= r * np.dot(d, a[-l - 1].T)             # BP3
            self.b[-l] -= r * np.sum(d, axis=1, keepdims=True)   # BP4
```

用 {{< xref eg="4-1" anchor="eg-network" />}} 训练一个 784–100–10 的网络，
一轮迭代后在 MNIST 上的准确率就超过 90%，最终收敛到 96% 附近：

```console {num="4-2" caption="MNIST 测试集上的十轮迭代，每轮一行。" #eg-training}
$ python net.py
Round 0: 9136/10000
Round 1: 9265/10000
Round 2: 9327/10000
Round 3: 9387/10000
Round 4: 9418/10000
Round 5: 9470/10000
Round 6: 9469/10000
Round 7: 9484/10000
Round 8: 9509/10000
Round 9: 9539/10000
```

> [!NOTE] 为什么 96% 并不是个好结果
>
> 剩下的那 4% 才是正题。二次代价会在 \(\sigma'(z)\) 很小的地方饱和，于是错得越离谱的输出
> 学得 *越慢*——恰好反了。把代价换成交叉熵
> \(C = -\frac{1}{n}\sum \bigl[y \ln a + (1-y)\ln(1-a)\bigr]\)，
> 就能把 {{< xref eq="4.3" anchor="eq-bp1" />}} 里的 \(\sigma'(z^{L})\) 因子约掉，
> 饱和随之消失。那是另一章的事，也是另一组方程。

## 合上这本书 {#close-book}

这一章用的是与前三章完全相同的编号机制：
{{< xref eq="4.1" anchor="eq-layer" />}} 与
{{< xref tbl="4-2" anchor="tbl-backprop" />}} 可以被任何一章引用，
就像引用
{{< xref page="chapter-one" tbl="1-1" anchor="tbl-baseline" >}}第一章的基线表{{< /xref >}}
一样。数学在这里是一种内容类型，而不是一种特殊模式。

## 参考文献 {#references}

[^nielsen]: Michael Nielsen. [*Neural Networks and Deep Learning*](http://neuralnetworksanddeeplearning.com/), Determination Press, 2015. 第二章用更长的篇幅推导了同样这四个方程。
[^whyz]: 误差之所以定义在带权输入 \(z\) 而非激活值 \(a\) 上，是因为这样 BP2 才是一个矩阵乘法；定义在 \(a\) 上也能推下去，只是递推式会难看得多。
