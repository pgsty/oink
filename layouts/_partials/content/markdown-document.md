{{- /*

Shared body of the semantic Markdown page output. The context is the page to
render. layouts/all.md wraps it for the per-page markdown output format, and
layouts/list.llmsfull.txt concatenates it per page for the opt-in section
full-text bundle -- the same renderer, so the two outputs cannot drift apart.
The caller owns setting the page's tdOutputFormat store flag to "markdown"
before rendering. The .md extension is load-bearing: an .html partial runs
under html/template autoescaping and entity-escapes the Markdown it emits.

Template design:

- This partial generates a title followed by zero or more sections.
- The title, and each section, are designed under the assumption that it is the
  last page element, and so does not add extra trailing newlines.
- Each section, other than the first, shall introduce a separator line.

*/ -}}
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
{{ T "markdown_llms_index" }} [ {{- path.Base $llmsIndexURL -}} ]( {{- $llmsIndexURL -}} )
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

{{ T "markdown_section_pages" }}

{{ range . -}}
- [ {{- .Title | strings.TrimSpace -}} ]( {{- .RelPermalink -}} )
  {{- with .Description | strings.TrimSpace -}}
    : {{ . -}}
  {{ end }}
{{ end -}}
{{ $needSeparator = true -}}

{{ end -}}

{{/* Backlinks, when the policy is on and pages link here -------------- */ -}}

{{ with partial "backlinks-sources.html" . -}}

{{ if $needSeparator }}
---

{{ else }}
{{ end -}}

{{ T "markdown_backlinks" }}

{{ range . -}}
- [ {{- .LinkTitle | default .Title | strings.TrimSpace -}} ]( {{- .RelPermalink -}} )
{{ end -}}

{{ end -}}
