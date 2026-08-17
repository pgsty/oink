---
title: Enhanced code blocks
description: Regression fixtures for the shared Chroma shell and code groups.
outputs: [HTML, markdown]
weight: 20
---

## Titled, numbered, and highlighted

```yaml {filename="config/very-long-example-name-for-responsive-layout.yml" copy="all" lineNos="table" lineNoStart=3 hl_lines="4 6"}
params:
  offline_search: true
  ui:
    sidebar_menu_foldable: true
    sidebar_menu_compact: true
```

## Escaped generic attributes

```text {#generic-code .code-fixture data-note="a \"quoted\" & value"}
safe attributes
```

## Wrapped and collapsed

```text {id="wrapped-example" wrap=true collapse=4 label="Wrapped configuration example"}
alpha = one
beta = two
gamma = this-is-a-deliberately-long-unbroken-value-that-tests-responsive-wrapping-without-changing-the-source
delta = four
epsilon = five
zeta = six
eta = seven
```

## Console commands

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

## Shell language label

```sh {copy=false}
echo "displayed as Bash"
```

## Package managers (adjacent fences, synchronized group)

```bash {tab="npm" group="package-manager" value="npm"}
npm install @example/client
```

```bash {tab="pnpm" value="pnpm"}
pnpm add @example/client
```

```bash {tab="yarn" value="yarn"}
yarn add @example/client
```

## Synchronized peer

```bash {tab="npm" group="package-manager" value="npm"}
npm install --global @example/tool
```

```bash {tab="pnpm" value="pnpm"}
pnpm add --global @example/tool
```

## Local tabs without a group (no hash / persistence)

```text {tab="A **literal** [label]"}
punctuation stays literal
```

```yaml {tab="YAML" title="config.yaml"}
message: title and tab coexist
```

## Full form: `{{</* tabs */>}}` with Markdown bodies

{{< tabs group="setting" default="conf" label="MinIO settings" >}}
{{< tab label="Environment Variable" value="env" >}}
###### `MINIO_LOGGER_WEBHOOK_QUEUE_DIR` {#envvar-queue-dir}

Set the queue directory through the environment.

```bash
export MINIO_LOGGER_WEBHOOK_QUEUE_DIR=/var/lib/minio/queue
```
{{< /tab >}}
{{< tab label="Configuration Setting" value="conf" >}}
###### `logger_webhook queue_dir` {#conf-queue-dir}

Set it with `mc admin config set`.

> [!TIP]
> Callouts and other blocks work inside tabs.
{{< /tab >}}
{{< /tabs >}}

Local (ungrouped) tabs:

{{< tabs >}}
{{< tab label="First" >}}
First body with a table:

| A | B |
| --- | --- |
| 1 | 2 |
{{< /tab >}}
{{< tab label="Second" >}}
Second body.
{{< /tab >}}
{{< /tabs >}}
