{{/*

Template design:

- This file generates a title followed by zero or more sections.
- The title, and each section, are designed under the assumption that it is the
  last page element, and so does not add extra trailing newlines.
- Each section, other than the first, shall introduce a separator line.

*/ -}}
{{- .Page.Store.Set "tdOutputFormat" "markdown" -}}

# {{ .Title | strings.TrimSpace -}}

{{/* Only advertise the site index on sites that actually publish it. A site can
enable the markdown output format without LLMS, and linking an unpublished
llms.txt would emit a dangling link on every Markdown page. */ -}}
{{ $llmsIndexURL := "" -}}
{{ with .Site.Home.OutputFormats.Get "llms" }}{{ $llmsIndexURL = .RelPermalink }}{{ end -}}
{{ $needSeparator := false -}}
{{/* The empty else branch in each separator block below emits a single
newline and is load-bearing; do not "simplify" it away. */ -}}

{{/* Description ------------------------------------------------------- */ -}}

{{ with .Description | strings.TrimSpace }}

> {{ replace . "\n" "\n> " -}}
{{ $needSeparator = true -}}
{{ end -}}

{{/* Site index -------------------------------------------------------- */ -}}

{{ if $llmsIndexURL }}
{{ if $needSeparator }}
---

{{ else }}
{{ end -}}

{{/* Link this language's index. `relURL` would point every translation at the
default language's llms.txt even though Hugo publishes one per language. */ -}}
LLMS index: [ {{- path.Base $llmsIndexURL -}} ]( {{- $llmsIndexURL -}} )
{{ $needSeparator = true -}}
{{ end -}}

{{/* Page content ------------------------------------------------------ */ -}}

{{ with .RenderShortcodes | strings.TrimSpace -}}
{{ if $needSeparator }}
---

{{ else }}
{{ end -}}

{{ . }}
{{ $needSeparator = true -}}
{{ end -}}

{{/* Section index, if any --------------------------------------------- */ -}}

{{ with .Pages -}}

{{ if $needSeparator }}
---

{{ else }}
{{ end -}}

Section pages:

{{ range . -}}
- [ {{- .Title | strings.TrimSpace -}} ]( {{- .RelPermalink -}} )
  {{- with .Description | strings.TrimSpace -}}
    : {{ . -}}
  {{ end }}
{{ end -}}

{{ end -}}
