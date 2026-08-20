---
title: 发布流程
description: 把经过评审的变更变成可追溯的发布。
book_kind: chapter
book_number: 2
book_status: draft
weight: 20
outputs: [HTML, print, markdown]
---

> *没有打上标签，就等于没有发布。*
>
> —— 发布工程的老话

第一章通过 {{< xref page="chapter-one" fig="1-1" anchor="fig-overview" />}} 建立了基线，本章沿着同一项变更走完发布流程，并且自始至终坚持一件事：在任何一个环节，都有人能指出正在讨论的究竟是哪一份字节。

## 明确区分交付状态 {#delivery-states}

本地修改、提交、推送与生产部署是彼此独立的状态。把它们分别记录，发布过程才容易审计。

{{< fig num="2-1" id="fig-release" src="/images/releasenote.webp" alt="OINK 发布说明页面" caption="发布说明把已交付制品与验证证据连接起来。" width="600" height="300" />}}

{{< tbl num="2-1" id="tbl-release" caption="各交付阶段需要的证据。" >}}
| 阶段 | 证据 | 负责人 |
| --- | --- | --- |
| 构建 | 可复现的制品 | 维护者 |
| 发布 | 远端校验和 | 发布工程师 |
| 部署 | 实际运行版本 | 运维人员 |
| 文档 | 读者可以钉住的版本号 | 作者 |
{{< /tbl >}}

下面这五种状态不是同义词。把它们混为一谈，是一个项目失去读者信任最常见的方式。
本地构建通过，五种状态一种也不算。

| 状态 | 何时达成 | 可撤销 | 证据 |
| --- | --- | --- | --- |
| 源码完成 | 变更已提交到发布分支 | 可以 | 一个 commit 哈希 |
| 已验证 | 该提交上全套检查通过 [^ci] | 可以 | 一次 CI 运行的链接 |
| 已发布 | 不可变的签名标签可经代理解析 [^immutable] | **不可以** | `GOPROXY` 返回该版本 |
| 已文档化 | 消费站点钉住了这个已发布版本 | 可以 | `go.mod` 里的一处 diff |
| 已部署 | 读者实际拿到的就是被钉住的版本 | 可以 | 一个响应头 |
{#tbl-states num="2-2" caption="发布状态及其顺序，其中只有一种无法撤销。"}

{{< xref tbl="2-2" anchor="tbl-states" />}} 中那唯一不可逆的一行，解释了为什么发布要放在最后，
也解释了为什么出错之后是发一个新的补丁版本，而不是把标签挪一挪。

## 先写清单 {#manifest}

先写下你打算交付什么，再去交付。清单就是日后评审者用来和现实做 diff 的那份东西。

{{< eg num="2-1" id="eg-manifest" caption="记录一份不可变的发布清单。" >}}
```yaml
version: 0.5.0
artifact: oink-0.5.0.tar.gz
sha256: verified
status: staged
```
{{< /eg >}}

校验和要与制品放在一起，并且直接采用验证工具本来就读得懂的格式。
凡是必须先手工改写一遍才能校验的东西，最后都不会有人去校验。

```text {num="2-2" caption="无需任何编辑就能交给 sha256sum -c 的校验和文件。" #eg-checksums}
9d3f0c1c7bd2f9b0a8b9a0f2c7c1c26f1e2ab0d1c4c6ba0d1e0a9f8c7b6a5d4e  oink-0.5.0.tar.gz
1a2b3c4d5e6f708192a3b4c5d6e7f80912a3b4c5d6e7f8091a2b3c4d5e6f70819  oink-0.5.0.zip
```

打标签是唯一收不回来的一步，所以本书也只有这一步是以终端会话、而不是以文件的形式呈现的。

```console {num="2-3" caption="发布：写注释、签名、推送，再用读者会用的那个代理验证一遍。" #eg-tag}
$ git tag -s v0.5.0 -m 'oink v0.5.0'
$ git push origin v0.5.0
To github.com:pgsty/oink.git
 * [new tag]         v0.5.0 -> v0.5.0
$ GOPROXY=https://proxy.golang.org go list -m github.com/pgsty/oink@v0.5.0
github.com/pgsty/oink v0.5.0
```

> [!DETAILS] 完整的验证输出
> ```text
> gpg: Signature made Mon Aug 18 21:04:11 2026 CST
> gpg:                using RSA key 6F2A1C3E7B9D0A45
> gpg: Good signature from "OINK Release <release@example.org>" [ultimate]
> go: downloading github.com/pgsty/oink v0.5.0
> go: verifying github.com/pgsty/oink@v0.5.0: checksum matches
> ```

## 给就绪度打分 {#readiness}

{{< eq num="2.1" id="eq-readiness" caption="一个简单的发布就绪度评分。" >}}
R = \frac{B + T + D}{3}
{{< /eq >}}

标签只发布一次，却会从许多镜像被取走，读者命中的是离自己最近的那一个。
若单个镜像已同步该版本的概率为 \(p\)，客户端可以在 \(n\) 个镜像之间回退，
那么这个版本可被解析的概率为：

$$
P_{\text{resolve}}(n) = 1 - (1 - p)^{n}
$$
{#eq-propagation num="2.2" caption="n 个相互独立的镜像中至少有一个已能提供该标签的概率。"}

这个指数解释了为什么"我这里没问题"不能算作已发布的证据：对手握源仓库的作者来说，
{{< xref eq="2.2" anchor="eq-propagation" />}} 早就接近 1；对没有源仓库的读者来说，
还远远不是。

## 交接 {#handoff}

{{< xref eg="2-1" anchor="eg-manifest" />}} 里的清单与
{{< xref tbl="2-1" anchor="tbl-release" />}} 里的阶段描述的是不同的证据，不应压缩成一个状态。
第三章把 {{< xref eq="2.1" anchor="eq-readiness" />}} 作为运行复盘的输入，并重新读一遍
{{< xref page="chapter-one" tbl="1-2" anchor="tbl-outputs" >}}第一章的输出矩阵{{< /xref >}}，
以确定这次复盘必须覆盖哪些界面。

## 参考文献 {#references}

[^ci]: [Continuous Delivery: Reliable Software Releases through Build, Test, and Deployment Automation](https://www.oreilly.com/library/view/continuous-delivery-reliable/9780321670250/). Jez Humble、David Farley 著, Addison-Wesley, 2010.
[^immutable]: [Go Modules Reference: Version queries and the checksum database](https://go.dev/ref/mod#checksum-database). *go.dev*, 2026 年查阅.
