---
title: Formulas and derivations
description: What a chapter looks like when the argument is carried by mathematics rather than by prose.
book_kind: chapter
book_number: 4
weight: 40
outputs: [HTML, print, markdown]
---

> *Do not worry about your difficulties in Mathematics. I can assure you mine are still greater.*
>
> — Albert Einstein, letter to Barbara Wilson (1943)

Chapters one to three carried their arguments in tables. This one carries it in
equations, which asks three things of a book system that prose never does: inline
formulas must sit inside a sentence without changing its line height, display
formulas must be numbered and referable from another chapter, and a derivation
must be able to run over several aligned lines without becoming an image.

The worked example is backpropagation — old, small enough to state completely,
and unforgiving about notation.[^nielsen]

## Fix the notation {#notation}

Every symbol used later is introduced once, in a table, with its shape. A reader
who loses track of whether \(W\) is a matrix or a list of matrices has lost the
chapter, and no amount of prose recovers it.

| Name | Symbol | Shape | Meaning |
| --- | :---: | :---: | --- |
| Input | \(x = a^{1}\) | \(d_1 \times 1\) | The activation of the input layer |
| Weights | \(W^{l}\) | \(d_l \times d_{l-1}\) | Layer \(l-1\) to layer \(l\); one row per neuron |
| Bias | \(b^{l}\) | \(d_l \times 1\) | One scalar per neuron |
| Weighted input | \(z^{l} = W^{l} a^{l-1} + b^{l}\) | \(d_l \times 1\) | What the activation function receives |
| Activation | \(a^{l} = \sigma(z^{l})\) | \(d_l \times 1\) | What the layer emits |
| Error | \(\delta^{l} \equiv \partial C / \partial z^{l}\) | \(d_l \times 1\) | Sensitivity of the cost to the weighted input [^whyz] |
{#tbl-notation num="4-1" caption="Notation for an L-layer network. Layers are counted from 1; the input layer has no weights of its own."}

## From one neuron to a layer {#one-layer}

A single neuron computes a weighted sum and passes it through an activation
function. Writing the layer's neurons as rows of one matrix turns \(d_l\) scalar
equations into one:

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
{#eq-layer num="4.1" caption="Forward pass for one layer, written once instead of once per neuron."}

The activation function is almost always the logistic sigmoid, chosen less for
its shape than for the second line below: its derivative is a product of values
the forward pass has already computed.

$$
\begin{aligned}
\sigma(z) &= \frac{1}{1 + e^{-z}} \\[4pt]
\sigma'(z) &= \sigma(z)\bigl(1 - \sigma(z)\bigr) = a \odot (1 - a)
\end{aligned}
$$
{#eq-sigmoid num="4.2" caption="The sigmoid and its derivative; ⊙ is the elementwise (Hadamard) product."}

## The four equations {#four-equations}

Backpropagation is four equations. The first gives the error at the output
layer, the second moves it one layer back, and the last two turn the error of a
layer into the gradients of that layer's parameters.

| Equation | What it needs | Number |
| --- | --- | :---: |
| \(\delta^{L} = \nabla_a C \odot \sigma'(z^{L})\) | The output \(a^{L}\) and the label \(y\) | BP1 |
| \(\delta^{l} = \bigl(W^{l+1}\bigr)^{\mathsf{T}} \delta^{l+1} \odot \sigma'(z^{l})\) | The next layer's weights and error | BP2 |
| \(\nabla_{W^{l}} C = \delta^{l} \bigl(a^{l-1}\bigr)^{\mathsf{T}}\) | This layer's error, the previous layer's output | BP3 |
| \(\nabla_{b^{l}} C = \delta^{l}\) | This layer's error, and nothing else | BP4 |
{#tbl-backprop num="4-2" caption="The four backpropagation equations. Only BP2 is recursive; the other three are local."}

Under the quadratic cost \(C = \tfrac{1}{2}\lVert y - a^{L} \rVert^{2}\) and a
sigmoid activation, BP1 and BP2 specialise to expressions in quantities the
forward pass already stored:

$$
\delta^{L} = (a^{L} - y) \odot (1 - a^{L}) \odot a^{L}
$$
{#eq-bp1 num="4.3" caption="BP1 under quadratic cost and sigmoid activation — no derivative is evaluated at run time."}

## Prove the transfer equation {#prove-bp2}

BP2 is the only one worth proving here, because it is the only one where the
choice of \(z\) rather than \(a\) in the definition of \(\delta\) pays off. Take
the definition, introduce the next layer's weighted inputs as intermediate
variables, and apply the chain rule:

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

The sum in the last line is a dot product between the next layer's error vector
and column \(j\) of the next layer's weight matrix. Taking that column is the
same as taking row \(j\) of the transpose, which is where the \(\mathsf{T}\) in
{{< xref tbl="4-2" anchor="tbl-backprop" />}} comes from — the transpose is not a
notational flourish, it is the whole content of the equation.

## Fifty lines of it {#implementation}

The four equations translate to four lines of array code, and a chapter that
states them should show that translation rather than assert it.

```python {num="4-1" caption="Stochastic gradient descent over mini-batches; the four marked lines are BP1 to BP4." #eg-network}
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
        for l in self.layers:                                    # forward
            a.append(1.0 / (1.0 + np.exp(-np.dot(self.w[l], a[-1]) - self.b[l])))

        d = (a[-1] - y) * a[-1] * (1 - a[-1])                    # BP1
        for l in range(1, self.L):
            if l > 1:
                d = np.dot(self.w[-l + 1].T, d) * a[-l] * (1 - a[-l])   # BP2
            self.w[-l] -= r * np.dot(d, a[-l - 1].T)             # BP3
            self.b[-l] -= r * np.sum(d, axis=1, keepdims=True)   # BP4
```

A network of 784–100–10 neurons trained by
{{< xref eg="4-1" anchor="eg-network" />}} passes 90% accuracy on MNIST after one
epoch and settles near 96%:

```console {num="4-2" caption="Ten epochs on the MNIST test set, one line per epoch." #eg-training}
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

> [!NOTE] Why 96% is not a good result
>
> The last four percent are the whole subject. A quadratic cost saturates
> wherever \(\sigma'(z)\) is small, so a badly wrong output learns *slowly* —
> precisely backwards. Replacing the cost with cross entropy,
> \(C = -\frac{1}{n}\sum \bigl[y \ln a + (1-y)\ln(1-a)\bigr]\), cancels the
> \(\sigma'(z^{L})\) factor in {{< xref eq="4.3" anchor="eq-bp1" />}} and removes
> the saturation. That is a different chapter, and a different set of equations.

## Close the book {#close-book}

This chapter used the same numbering machinery as the other three:
{{< xref eq="4.1" anchor="eq-layer" />}} and
{{< xref tbl="4-2" anchor="tbl-backprop" />}} are addressable from any chapter,
exactly like
{{< xref page="chapter-one" tbl="1-1" anchor="tbl-baseline" >}}the baseline table{{< /xref >}}.
Mathematics is a content type here, not a special mode.

## References {#references}

[^nielsen]: Michael Nielsen. [*Neural Networks and Deep Learning*](http://neuralnetworksanddeeplearning.com/), Determination Press, 2015. Chapter 2 derives the same four equations at greater length.
[^whyz]: The error is defined on the weighted input \(z\) rather than the activation \(a\) because it makes BP2 a matrix product; defining it on \(a\) works too, and produces an uglier recursion.
