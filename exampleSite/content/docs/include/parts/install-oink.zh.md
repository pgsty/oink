把 OINK 安装到一个已有的 Hugo 站点，三条命令：

```sh
hugo mod init github.com/you/your-site
hugo mod get github.com/pgsty/oink
hugo server
```

> [!NOTE]
> `hugo mod get` 需要本机安装 Go；用离线归档或 submodule 时不需要。

当前发布版本是 {{< param version >}}。
