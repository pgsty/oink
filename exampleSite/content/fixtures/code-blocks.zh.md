---
title: 增强代码块
description: 共享 Chroma 外壳与代码分组的回归样例。
outputs: [HTML, markdown]
weight: 20
---

## 带标题、行号与高亮

```yaml {filename="config/very-long-example-name-for-responsive-layout.yml" copy="all" lineNos="table" lineNoStart=3 hl_lines="4 6"}
params:
  offline_search: true
  ui:
    sidebar_menu_foldable: true
    sidebar_menu_compact: true
```

## 转义后的通用属性

```text {#generic-code .code-fixture data-note="a \"quoted\" & value"}
safe attributes
```

## 换行与折叠

```text {id="wrapped-example" wrap=true collapse=4 label="换行的配置示例"}
alpha = one
beta = two
gamma = this-is-a-deliberately-long-unbroken-value-that-tests-responsive-wrapping-without-changing-the-source
delta = four
epsilon = five
zeta = six
eta = seven
```

## 终端会话

```console
$ printf 'hello\n'
hello
$ printf 'world\n'
world
$ printf '%s\n' \
>   first \
>   second
first
second
```

## Shell 语言标记

```sh {copy=false}
echo "displayed as Bash"
```

## 包管理器（相邻围栏，同步分组）

```bash {tab="npm" group="package-manager" value="npm"}
npm install @example/client
```

```bash {tab="pnpm" value="pnpm"}
pnpm add @example/client
```

```bash {tab="yarn" value="yarn"}
yarn add @example/client
```

## 同组联动

```bash {tab="npm" group="package-manager" value="npm"}
npm install --global @example/tool
```

```bash {tab="pnpm" value="pnpm"}
pnpm add --global @example/tool
```

## 不分组的本地标签页（没有 hash 与持久化）

```text {tab="A **literal** [label]"}
punctuation stays literal
```

```yaml {tab="YAML" title="config.yaml"}
message: title and tab coexist
```

## 完整形态：带 Markdown 正文的 `{{</* tabs */>}}`

{{< tabs group="setting" default="conf" label="MinIO 设置" >}}
{{< tab label="环境变量" value="env" >}}
###### `MINIO_LOGGER_WEBHOOK_QUEUE_DIR` {#envvar-queue-dir}

通过环境变量设置队列目录。

```bash
export MINIO_LOGGER_WEBHOOK_QUEUE_DIR=/var/lib/minio/queue
```
{{< /tab >}}
{{< tab label="配置项" value="conf" >}}
###### `logger_webhook queue_dir` {#conf-queue-dir}

用 `mc admin config set` 设置它。

> [!TIP]
> 标签页里可以放提示块与其它块级内容。
{{< /tab >}}
{{< /tabs >}}

不分组的本地标签页：

{{< tabs >}}
{{< tab label="第一项" >}}
第一个正文，带一张表：

| A | B |
| --- | --- |
| 1 | 2 |
{{< /tab >}}
{{< tab label="第二项" >}}
第二个正文。
{{< /tab >}}
{{< /tabs >}}
