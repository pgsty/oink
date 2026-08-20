---
title: Asciinema
linkTitle: Asciinema
description: Put a .cast terminal recording on the page — the text stays selectable text, and the player ships with the theme rather than coming from a CDN.
icon: fa-solid fa-terminal
weight: 210
search_keywords: [Asciinema, terminal recording, cast, asciicast, screencast, demo, player]
---

`asciinema` renders a `.cast` recording as a terminal player on the page. It
suits command-line walkthroughs: the text in the terminal is still text, it can
be selected and copied, and the near-two-minute install excerpt on this page is
about 110 KB. Graphical interfaces belong in screenshots or video — this
component plays terminal recordings only. The player and its styles ship with
the theme, nothing is downloaded at build time, no CDN is contacted at runtime,
and only a page that uses it loads the runtime.

## Shortest form {#minimal}

`file` is the only required parameter:

```markdown {title="Source"}
{{</* asciinema file="images/install.cast" */>}}
```

{{< asciinema file="images/install.cast" >}}

The recording is a single-node Pigsty install on a Debian machine in a 120×36
terminal, trimmed to the first minute and 54 seconds. The file lives at
`static/images/install.cast` on this site, so the path is written from the site
root. A file under `assets/` is written as a relative path: the theme looks in
resources first and falls back to treating the value as a site-root path.
Without `title`, the window title shows the value of `file`.

## Window title and theme {#title-theme}

`title` sets the window title, `theme` the colours:

```markdown {title="Source"}
{{</* asciinema file="images/install.cast" title="Pigsty single-node install" theme="dracula" */>}}
```

{{< asciinema file="images/install.cast" title="Pigsty single-node install" theme="dracula" >}}

`theme` defaults to `auto`: it follows the site's colour scheme, `td-light` in
light and `td-dark` in dark, remounting in place when the reader switches. To
pin a terminal palette, the values are the player's own `asciinema`, `dracula`,
`gruvbox-dark`, `monokai`, `nord`, `seti`, `solarized-dark`, `solarized-light`,
`tango`, plus the theme's `td-light` / `td-dark`. A pinned theme stops following
the colour scheme, and `solarized-light` on a dark site does not have workable
contrast. The terminal font needs no setting: the player uses the site's code
font, the one the code blocks use.

## Speed, start point and poster {#playback}

Three parameters control where a long recording starts: `speed` sets the rate,
`startAt` skips the opening, `poster` decides the frame shown before playback.

```markdown {title="Source"}
{{</* asciinema file="images/install.cast" title="From 60 seconds in, at double speed"
  speed="2" startAt="60" poster="npt:1:30" */>}}
```

{{< asciinema file="images/install.cast" title="From 60 seconds in, at double speed" speed="2" startAt="60" poster="npt:1:30" >}}

`speed` and `startAt` are numbers (seconds) and `poster` uses the player's
`npt:` notation for a point in time, so `npt:1:30` is one minute thirty. The
player above rests on the frame at 90 seconds and starts playing from 60.

`idleTimeLimit` compresses silent stretches to at most N seconds. This recording
was already compressed while recording (`idle_time_limit: 0.5` in the `.cast`
header), so it does not need it. Only files recorded without an idle limit do.

## Size and fit {#size}

The player scales to the container width by default (`fit="width"`), and the
terminal's rows and columns come from the `.cast` header. `cols` / `rows`
override that:

```markdown {title="Source"}
{{</* asciinema file="images/install.cast" title="Only 16 rows tall" rows="16" */>}}
```

{{< asciinema file="images/install.cast" title="Only 16 rows tall" rows="16" >}}

A size smaller than the recording clips it — the one above shows 16 of the 36
rows. `cols` / `rows` exist to correct a wrong size in the recording's header;
they are not a layout tool. To make the player shorter, record again in a
smaller terminal.

`fit` takes four values: `width` (the default, scale to width), `height` (to
height), `both` (fit both axes) and `none` (no scaling — a wide terminal
overflows).

## Looping and preloading {#autoplay}

`loop` replays at the end, and `preload` fetches the `.cast` when the page
loads so pressing play does not wait:

```markdown {title="Source"}
{{</* asciinema file="images/install.cast" title="Looping: the first minute after login"
  startAt="0" speed="3" loop="true" preload="true" */>}}
```

{{< asciinema file="images/install.cast" title="Looping: the first minute after login" startAt="0" speed="3" loop="true" preload="true" >}}

`autoplay="true"` starts playback as the page opens. It is not recommended: a
"reduce motion" preference only disables the transitions on the player's
controls, it does not stop autoplay. When you really need it, pair it with
`loop`, keep the clip very short, and put only one on a page.

## Inside steps {#in-steps}

Put the recording next to the step: the text says what to do, the recording
shows what it looks like.

````markdown {title="Source"}
1. Install the dependencies and fetch the installer:

   ```sh
   curl -fsSL https://repo.pigsty.io/get | bash
   ```

2. Run the install; here are the first two minutes:

   {{</* asciinema file="images/install.cast" title="pig install" speed="4" */>}}

3. Open `http://<node address>:3000` and sign in to Grafana with `admin / pigsty`.
{.steps}
````

1. Install the dependencies and fetch the installer:

   ```sh
   curl -fsSL https://repo.pigsty.io/get | bash
   ```

2. Run the install; here are the first two minutes:

   {{< asciinema file="images/install.cast" title="pig install" speed="4" >}}

3. Open `http://<node address>:3000` and sign in to Grafana with `admin / pigsty`.
{.steps}

A page can hold several players, and the script and styles load once.

## Recording a cast file {#recording}

The theme only plays. Record with
[asciinema](https://docs.asciinema.org/) —
`asciinema rec --idle-time-limit=2 --cols=100 --rows=28 install.cast` — and
check it locally with `asciinema play install.cast`.

- Keep the terminal under 100 columns so it stays readable on a narrow screen,
  and `clear` before you start.
- Clear secrets first: a `.cast` is plain text and every character in the
  recording is greppable. Check before committing.
- Put the file in `static/images/` or in the page bundle and commit it. Do not
  reference a `.cast` URL on someone else's site.

## Output {#outputs}

| Output | Shape |
| --- | --- |
| HTML | A `<div class="td-asciinema">` window frame plus the player; the player CSS/JS and the init script load on demand, once per page |
| Print | As HTML — the print output loads the player too; on paper you get whichever frame was showing |
| Markdown | The same container HTML plus a JSON configuration block; the only readable text is the window title |
| RSS | The same static markup; readers do not run scripts, so an empty window frame is all that is left |

A recording must never be the only source of information. Write the key commands
and the key output beside it in text or a code block: offline readers, whatever
consumes `llms.txt`, and anyone printing the page see only that text.

## Parameter reference {#reference}

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `file` | path (required) | — | Named, or the first positional parameter; looked up as a global resource first, then as a site-root path; a full URL with a scheme is passed through unchanged |
| `title` | plain text | the value of `file` | The window title |
| `theme` | enum | `auto` | `auto` follows the site's colour scheme; or `td-light` `td-dark` `asciinema` `dracula` `gruvbox-dark` `monokai` `nord` `seti` `solarized-dark` `solarized-light` `tango` |
| `fit` | enum | `width` | `width` `height` `both` `none`; anything else fails the build |
| `cols` / `rows` | integer | from the `.cast` header | Override the terminal size; smaller than the recording clips it |
| `speed` | number | `1` | Playback rate |
| `startAt` | number (seconds) | `0` | Where playback starts |
| `idleTimeLimit` | number (seconds) | from the `.cast` header | Longest a silent stretch plays for |
| `poster` | string | — | The frame shown before playback, `npt:mm:ss` |
| `autoplay` | `"true"` / omitted | off | Play as the page opens; not recommended |
| `loop` | `"true"` / omitted | off | Replay at the end |
| `preload` | `"true"` / omitted | off | Fetch the `.cast` when the page loads |
| `pauseOnMarkers` | `"true"` / omitted | off | Pause at chapter markers |
| `markers` | `time:label,time:label` | — | Chapter markers; see the limits — the labels do not reach the player today |
{.fields meta="type default"}

The boolean-ish parameters compare against the text `true`: `loop="true"` and
`loop=true` both enable, anything else disables. `fit` is validated by the theme
and an illegal value errors with the parameter name. Numeric parameters
(`speed`, `cols`, `rows`, `startAt`, `idleTimeLimit`) fail conversion — and the
build — when they are not numbers.

## Limits {#limits}

- `markers` labels are lost: the theme flattens the `time:label` list into a
  one-dimensional array, and the player accepts only pairs, so the timeline ends
  up with unlabelled markers. When you need chapters, write a list beside the
  recording.
- The player needs JavaScript: with scripts disabled, and in Markdown and RSS
  output, only an empty window remains — see [Output](#outputs).
- Recordings are not searchable: the site index covers page text, so a command
  that only appears in a recording cannot be found.
- Do not reference a remote `.cast`: a `file` with a scheme is passed to the
  player unchanged, and the page then depends on someone else's site.
- Keep each clip short: few people finish a recording longer than five or six
  minutes. Split a long procedure into several short ones, each with its own
  text.

## Related {#related}

- [Code blocks](/docs/code/) — the key commands and output, copyable
- [Steps](/docs/steps/) — the recording beside the step it belongs to
- [Images](/docs/image/) — static screenshots: recordings for terminals, screenshots for graphical interfaces
- [Include](/docs/include/) — when the same commands appear on several pages
