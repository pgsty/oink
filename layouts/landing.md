{{- .Page.Store.Set "tdOutputFormat" "markdown" -}}
{{- partial "front-matter-legacy.html" . -}}
# {{ .Title | strings.TrimSpace }}
{{- with .Description | strings.TrimSpace }}

> {{ replace . "\n" "\n> " }}
{{- end }}
{{- $landing := partial "landing/data.html" . -}}
{{- with (partial "landing/text.html" (dict "page" . "data" $landing) | strings.TrimSpace) }}

{{ . | safeHTML }}
{{- end -}}
