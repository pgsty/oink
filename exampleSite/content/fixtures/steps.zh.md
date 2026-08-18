---
title: 步骤
linkTitle: 步骤
description: 有序列表步骤（原生形态）与标题步骤（完整形态）。
outputs: [HTML, markdown]
weight: 20
---

## 原生形态：有序列表

1. 安装依赖

   一个步骤里可以放任何块级内容：段落、围栏、提示块、嵌套列表。

   ```bash {tab="Homebrew" group="install" value="brew"}
   brew install pigsty
   ```
   ```bash {tab="APT" value="apt"}
   sudo apt install pigsty
   ```

1. ### 初始化工作区 {#init-workspace}

   步骤里的标题会进入页面目录。

   > [!TIP]
   > 提示块在步骤里同样可用。

1. 验证安装结果

   ```console
   $ pig --version
   pig 1.7.0
   ```
{.steps}

## 从第三步开始

3. 第三
1. 第四
1. 第五
{.steps}

## 完整形态：标题步骤

{{% steps %}}

### 写内容

一步一个标题。这个形态不需要缩进，也可以放 `%` 形式的容器 shortcode。

### 检查顺序

整步移动、增加或删除，编号会自动更新。

{{% /steps %}}
