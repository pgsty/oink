#!/usr/bin/env python3
"""Check preset palettes, Slate provenance, and real Hugo configuration output."""
from pathlib import Path
import json
import re
import tempfile

from test_site import ROOT, run_hugo_process


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
    paper_source = (ROOT/'assets/scss/td/_presets.scss').read_text()
    brand_source = (ROOT/'assets/scss/td/_brand.scss').read_text()
    baseline = json.loads((ROOT/'tests/goldens/presets/slate-v1.1.0.json').read_text())
    experiment_source = (ROOT/'assets/scss/td/_experimental-presets.scss').read_text()
    palettes = {preset: {mode: palette(source, mode, preset) for mode in ('light', 'dark')}
                for preset, source in [('paper', paper_source), ('ink', experiment_source), ('terminal', experiment_source)]}
    canvas_source = (ROOT/'layouts/_partials/_funcs/preset-canvases.html').read_text()
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
            for surface in ('--bs-body-bg', '--bs-secondary-bg', '--bs-tertiary-bg'):
                canvas = tokens[surface]
                for key in ('--bs-body-color', '--bs-secondary-color', '--bs-tertiary-color', '--bs-link-color', '--bs-link-hover-color', '--bs-code-color', '--td-brand-copper'):
                    values = sorted([luminance(canvas), luminance(tokens[key])])
                    ratio = (values[1]+.05)/(values[0]+.05)
                    assert ratio >= 4.5, f'{preset} {mode} {key} on {surface}: {ratio:.2f}:1'
        for source in (slate, *(modes[mode] for modes in palettes.values())):
            assert source['--bs-body-bg'] in canvas_source
            assert source['--bs-body-color'] in canvas_source
    fonts = (ROOT/'assets/scss/td/_tokens-typography.scss').read_text()
    assert fonts.index("[data-td-preset='paper']") < fonts.index("[data-td-typography='system']")
    assert '--td-brand-font-family:' in fonts.split("[data-td-typography='system']")[1]

    cases = [
        ('default', '', 'paper', False, False),
        ('slate', '    preset: slate\n    dark_mode: true\n    preset_menu: true\n', 'slate', True, True),
        ('style-only', '    preset_menu: [paper, slate]\n    typography: system\n    fonts:\n      brand: serif\n', 'paper', True, False),
        ('fixed', '    preset: slate\n    preset_menu: [slate]\n', 'slate', False, False),
        ('ink-default', "    preset: ink\n    preset_menu: true\n    theme_color: '#245f94'\n", 'ink', True, False),
        ('terminal-fixed', "    preset: terminal\n    theme_color: '#245f94'\n", 'terminal', False, False),
        ('experiments', '    preset_menu: [paper, slate, ink, terminal]\n    dark_mode: true\n', 'paper', True, True),
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
            expected = {'paper', 'slate', 'ink', 'terminal'} if name == 'experiments' else (
                {'paper', 'slate', 'ink'} if name == 'ink-default' else {'paper', 'slate'} if menu else set())
            assert offered == expected, (name, offered, expected)
            assert 'td-appearance__swatch' not in html
            assert 'td-appearance__experimental' not in html
            for value in offered:
                assert f'td-appearance__preset-icon--{value}' in html
            if name == 'style-only':
                assert 'data-td-typography="system"' in html
                assert '--td-brand-font-family:serif' in html.replace(' ', '')
    print(f'Preset check passed: Paper/Ink/Terminal AA on 3 surfaces and token parity; Slate v1.1.0 palette; {len(cases)} configuration builds and {len(cases)*4} root outputs')


if __name__ == '__main__':
    main()
