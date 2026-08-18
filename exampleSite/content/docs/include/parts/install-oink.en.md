Installing OINK into an existing Hugo site takes three commands:

```sh
hugo mod init github.com/you/your-site
hugo mod get github.com/pgsty/oink
hugo server
```

> [!NOTE]
> `hugo mod get` needs Go on the machine; an offline archive or a submodule does not.

The current release is {{< param version >}}.
