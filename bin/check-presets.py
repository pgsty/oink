#!/usr/bin/env python3
"""Check preset palettes, Slate provenance, and real Hugo configuration output."""
from pathlib import Path
import json
import re
import tempfile

from test_site import ROOT, run_hugo_process


def resolver_names(group):
    """A preset-name slice of the resolver, which owns the available names."""
    source = (ROOT/'layouts/_partials/preset-config.html').read_text()
    return tuple(re.findall(r'"([a-z]+)"', re.search(r'\$' + group + r'\s*:=\s*slice((?:\s+"[a-z]+")+)', source)[1]))


# Presets whose palettes live in experimental-presets.css, in menu order.
EXPERIMENTS = resolver_names('experimental')
ALL = (*resolver_names('stable'), *EXPERIMENTS)
assert ALL[:2] == ('paper', 'slate'), ALL
# The Appearance trigger's color-choice slot (head.html names the attribute in
# a selector too, so match an element).
THEME_ICON = re.compile(r'<span[^>]*\sdata-td-theme-icon[\s>]')


def declarations(block):
    return dict(re.findall(r'(--[\w-]+):\s*([^;]+);', block))


def palette(source, mode, preset=None):
    selector = (rf"\[data-td-preset='{preset}'\]" if mode == 'light'
                else rf"\[data-td-preset='{preset}'\] \[data-bs-theme='dark'\]") if preset else (
                r"\[data-bs-theme='light'\]" if mode == 'light' else r"\[data-bs-theme='dark'\]")
    return declarations(re.search(selector + r'\s*\{([^}]+)', source)[1])


def luminance(color):
    rgb = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
    linear = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb]
    return sum(c*w for c, w in zip(linear, [.2126, .7152, .0722]))


def main():
    paper_source = (ROOT/'assets/css/td/presets.css').read_text()
    brand_source = (ROOT/'assets/css/td/brand.css').read_text()
    baseline = json.loads((ROOT/'tests/goldens/presets/slate-v1.1.0.json').read_text())
    experiment_source = (ROOT/'assets/css/td/experimental-presets.css').read_text()
    palettes = {preset: {mode: palette(source, mode, preset) for mode in ('light', 'dark')}
                for preset, source in [('paper', paper_source), *((name, experiment_source) for name in EXPERIMENTS)]}
    canvas_source = (ROOT/'layouts/_partials/_funcs/preset-canvases.html').read_text()
    canvases = {name: dict(re.findall(r'"(\w+)" "(#[0-9a-f]{6})"', body))
                for name, body in re.findall(r'"(\w+)" \(dict ([^)]*)\)', canvas_source)}
    assert set(canvases) == set(ALL), f'pre-paint canvas map names {sorted(canvases)}'
    contrast_source = (ROOT/'layouts/_partials/_funcs/contrast-on-canvas.html').read_text()
    canvas_luminances = {name: {'light': float(light), 'dark': float(dark)}
                        for name, light, dark in re.findall(r'"(\w+)" \(dict "light" ([0-9.]+) "dark" ([0-9.]+)\)', contrast_source)}
    for preset, modes in palettes.items():
        assert modes['light'].keys() == modes['dark'].keys(), f'{preset} light/dark token parity'
    for mode in ('light', 'dark'):
        slate = palette(brand_source, mode)
        for key, value in baseline['palettes'][mode].items():
            actual = slate[key]
            # The historical palette remains the provenance; opaque focus
            # indicators deliberately correct its translucent focus token.
            if key == '--bs-focus-ring-color':
                assert actual == 'var(--bs-link-color)', 'focus ring must use the opaque accessible link token'
                continue
            # The optional preset-accent indirection retains the same fallback.
            actual = re.sub(r'var\(--td-preset-accent(?:-rgb|-hover)?, (var\([^)]+\))\)', r'\1', actual)
            assert actual == value, f'Slate {mode} changed {key}: {actual} != {value}'
        for preset, modes in palettes.items():
            tokens = modes[mode]
            assert abs(luminance(tokens['--bs-body-bg']) - canvas_luminances[preset][mode]) < 0.000001, f'{preset} {mode} advisory canvas luminance'
            assert not any(key.startswith('--td-accent') for key in tokens), 'preset masks authored theme_color'
            # A preset that shades its canvas (Ink's paper, News's
            # safelight) names the shade's extreme as a surface, so text is
            # checked where the page is darkest or brightest, not only at the
            # flat canvas color.
            if preset in ('ink', 'news'):
                assert '--td-preset-canvas-edge' in tokens, f'{preset} {mode} names its canvas edge'
            surfaces = ('--bs-body-bg', '--bs-secondary-bg', '--bs-tertiary-bg',
                        *(('--td-preset-canvas-edge',) if '--td-preset-canvas-edge' in tokens else ()))
            texts = ('--bs-body-color', '--bs-secondary-color', '--bs-tertiary-color', '--bs-link-color', '--bs-link-hover-color', '--bs-code-color', '--td-brand-copper')
            for surface in surfaces:
                canvas = tokens[surface]
                for key in texts:
                    values = sorted([luminance(canvas), luminance(tokens[key])])
                    ratio = (values[1]+.05)/(values[0]+.05)
                    assert ratio >= 4.5, f'{preset} {mode} {key} on {surface}: {ratio:.2f}:1'
        # The pre-paint canvas map must name exactly each stylesheet's
        # canvas and ink, preset by preset and mode by mode.
        for preset, tokens in (('slate', slate), *((name, modes[mode]) for name, modes in palettes.items())):
            assert canvases[preset][mode] == tokens['--bs-body-bg'].lower(), f'{preset} {mode} pre-paint canvas'
            assert canvases[preset][f'{mode}Ink'] == tokens['--bs-body-color'].lower(), f'{preset} {mode} pre-paint ink'
    # A canvas edge is checked for contrast only if it is the shade the page
    # really paints: Ink's gradient ends on the token, and News's dark glow,
    # the accent at a low alpha over the canvas, peaks at it. Light News has
    # no glow, so its edge is the canvas itself.
    def rgb(color):
        return [int(color[i:i+2], 16) for i in (1, 3, 5)]
    ink_paper = re.search(r"\[data-td-preset='ink'\] body \{([^}]+)\}", experiment_source)[1]
    assert re.search(r'radial-gradient\([^;]*var\(--td-preset-canvas-edge\)\)', ink_paper), 'Ink paper shade ends on its canvas edge'
    glow = re.search(r"\[data-td-preset='news'\]\[data-bs-theme='dark'\] body \{([^}]+)\}", experiment_source)[1]
    alpha = float(re.search(r'rgba\(var\(--td-preset-accent-rgb\), ([0-9.]+)\)', glow)[1])
    news_dark = palettes['news']['dark']
    accent = [int(part) for part in news_dark['--td-preset-accent-rgb'].split(',')]
    peak = [round(c + (a - c) * alpha) for c, a in zip(rgb(news_dark['--bs-body-bg']), accent)]
    edge = rgb(news_dark['--td-preset-canvas-edge'])
    assert all(abs(e - p) <= 1 for e, p in zip(edge, peak)), f'News dark canvas edge {edge} != glow peak {peak}'
    news_light = palettes['news']['light']
    assert news_light['--td-preset-canvas-edge'] == news_light['--bs-body-bg'], 'light News has no glow'
    fonts = (ROOT/'assets/css/td/tokens-typography.css').read_text()
    assert fonts.index("[data-td-preset='paper']") < fonts.index("[data-td-typography='system']")
    assert '--td-brand-font-family:' in fonts.split("[data-td-typography='system']")[1]
    for preset in ('paper', *EXPERIMENTS):
        for mode in ('light', 'dark'):
            giscus_css = (ROOT/f'assets/css/giscus-{preset}-{mode}.css').read_text()
            assert '@import' not in giscus_css and 'https://' not in giscus_css
            for required_token in ('--color-btn-primary-hover-bg:', '--color-action-list-item-default-hover-bg:'):
                assert required_token in giscus_css, (preset, mode, required_token)
            scale_token = '--color-scale-gray-1:' if mode == 'light' else '--color-scale-gray-7:'
            assert scale_token in giscus_css, (preset, mode, scale_token)

    cases = [
        ('default', '', 'paper', False, False),
        ('slate', '    preset: slate\n    dark_mode: true\n    preset_menu: true\n', 'slate', True, True),
        ('style-only', '    preset_menu: [paper, slate]\n    typography: system\n    fonts:\n      brand: serif\n', 'paper', True, False),
        ('main-face', '    fonts: {ui: serif}\n', 'paper', False, False),
        ('separate-faces', '    fonts: {ui: sans-serif, body: serif, heading: monospace}\n', 'paper', False, False),
        ('prose-face', '    fonts: {body: serif}\n', 'paper', False, False),
        ('fixed', '    preset: slate\n    preset_menu: [slate]\n', 'slate', False, False),
        ('ink-default', "    preset: ink\n    preset_menu: true\n    theme_color: '#245f94'\n", 'ink', True, False),
        ('terminal-fixed', "    preset: terminal\n    theme_color: '#245f94'\n", 'terminal', False, False),
        ('experiments', '    preset_menu: [paper, slate, ink, terminal]\n    dark_mode: true\n', 'paper', True, True),
        ('all', '    preset_menu: [' + ', '.join(reversed(ALL)) + ']\n    dark_mode: true\n', 'paper', True, True),
        ('news-fixed', '    preset: news\n', 'news', False, False),
        ('github-mode-only', '    preset: github\n    dark_mode: true\n', 'github', False, True),
    ]
    with tempfile.TemporaryDirectory(prefix='oink-presets-') as tmp:
        for name, config, preset, menu, dark in cases:
            site = Path(tmp)/name
            (site/'content/docs').mkdir(parents=True)
            (site/'content/docs/_index.md').write_text('---\ntitle: Docs\n---\n\n## Heading\n\nText and `code`.\n')
            (site/'hugo.yaml').write_text('baseURL: https://example.org/sub/\ntitle: Presets\ntheme: oink\noutputs:\n  section: [HTML, print]\nparams:\n  ui:\n'+(config or '    preset_menu: false\n'))
            result = run_hugo_process(['hugo', '--source', str(site), '--themesDir', str(ROOT.parent), '--destination', str(site/'public'), '--printPathWarnings'],capture_output=True,text=True)
            assert result.returncode == 0, result.stdout+result.stderr
            for path in ('index.html', 'docs/index.html', '404.html', '_print/docs/index.html'):
                html = (site/'public'/path).read_text()
                assert f'data-td-preset="{preset}"' in html, (name, path)
                assert f'data-td-site-preset="{preset}"' in html, (name, path)
            html = (site/'public/docs/index.html').read_text()
            assert ('data-td-preset-value=' in html) == menu, name
            assert ('data-bs-theme-value=' in html) == dark, name
            assert ("getItem('td-preset')" in html) == menu, name
            offered = set(re.findall(r'data-td-preset-value="([a-z]+)"', html))
            expected = {'paper', 'slate', 'ink', 'terminal'} if name == 'experiments' else set(ALL) if name == 'all' else (
                {'paper', 'slate', 'ink'} if name == 'ink-default' else {'paper', 'slate'} if menu else set())
            assert offered == expected, (name, offered, expected)
            # The menu keeps one order whatever order a list gives, and lays
            # three, five or six styles out in three columns.
            order = list(dict.fromkeys(re.findall(r'data-td-preset-value="([a-z]+)"', html)))
            assert order == [preset for preset in ALL if preset in offered], (name, order)
            columns = re.findall(r'td-appearance__presets--(\d)', html)
            if menu:
                assert set(columns) == {'3' if len(offered) in (3, 5, 6) else '2'}, (name, columns)
                assert ('td-appearance__panel--wide' in html) == (len(offered) in (3, 5, 6)), name
                assert 'aria-keyshortcuts="T"' in html and '>(T)</span>' in html, name
            # The trigger shows the reader's color choice (sun, moon or the
            # system circle) whenever the panel offers Color, and a palette
            # only when it offers Style alone.
            if dark:
                assert 'aria-keyshortcuts="Y"' in html and '>(Y)</span>' in html, name
                assert THEME_ICON.search(html), name
                slot = re.search(r'data-td-theme-icon>(.*?)</span>\s*</button>', html, re.S)[1]
                for glyph in ('fa-sun', 'fa-moon', 'fa-circle-half-stroke'):
                    assert glyph in slot, (name, glyph)
            elif menu:
                assert not THEME_ICON.search(html), name
                assert re.search(r'data-td-appearance-trigger[^>]*>\s*<i class="[^"]*\btd-shell-icon--palette\b', html), name
            assert 'td-appearance__swatch' not in html
            assert 'td-appearance__experimental' not in html
            for value in offered:
                assert f'td-appearance__preset-icon--{value}' in html
            if name == 'style-only':
                assert 'data-td-typography="system"' in html
                assert '--td-brand-font-family:serif' in html.replace(' ', '')
            if name == 'main-face':
                assert '--td-body-font-family:var(--td-ui-font-family)' in html
                assert '--td-heading-font-family:var(--td-body-font-family)' in html
            if name == 'prose-face':
                assert '--td-body-font-family:serif' in html
                assert '--td-heading-font-family:var(--td-body-font-family)' in html
                assert '--td-body-font-family:var(--td-ui-font-family)' not in html
            if name == 'separate-faces':
                assert '--td-body-font-family:serif' in html
                assert '--td-heading-font-family:monospace' in html
                assert '--td-heading-font-family:var(--td-body-font-family)' not in html
    print(f'Preset check passed: {", ".join({"github": "GitHub"}.get(p, p.title()) for p in ("paper", *EXPERIMENTS))} AA on every surface (Ink and News also on their canvas edge) and token parity; Slate v1.1.0 palette; {len(cases)} configuration builds and {len(cases)*4} root outputs')


if __name__ == '__main__':
    main()
