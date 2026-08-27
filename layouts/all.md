{{/* The per-page semantic Markdown output. The body lives in the shared
content/markdown-document.md partial, which the LLMSFULL section bundle
concatenates page by page -- one renderer for both outputs. The partial keeps
a text extension on purpose: an .html partial would run under html/template
autoescaping and entity-escape the Markdown it emits. */ -}}
{{- .Page.Store.Set "tdOutputFormat" "markdown" -}}
{{- partial "content/markdown-document.md" . -}}
