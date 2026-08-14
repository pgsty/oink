{{- .Page.Store.Set "tdOutputFormat" "markdown" -}}
# {{ .Title | strings.TrimSpace }}
{{- with .Description | strings.TrimSpace }}

> {{ replace . "\n" "\n> " }}
{{- end }}
{{- $landing := partial "landing/data.html" . -}}
{{- with (partial "landing/text.html" (dict "page" . "data" $landing) | strings.TrimSpace) }}

{{ . | safeHTML }}
{{- end -}}
