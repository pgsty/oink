#!/usr/bin/env python3
"""Check translation-comparison discovery, lazy assets, output isolation and pane isolation."""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from test_site import ROOT, run_hugo_process, theme_warnings

LANGUAGES = ['en', 'zh', 'de', 'ru', 'fr', 'es', 'ja', 'ar']
GA_ID = 'G-TEST1234'

# Every browser runtime declares how it behaves inside a comparison pane.
# Shell runtimes stand down there; content runtimes keep working; the reader
# itself only ever runs in the host document. A new runtime must be classified.
PANE_SUPPRESSED = {
    'command-palette', 'compare-entry', 'docs-shell', 'feedback', 'footer-collapse', 'giscus',
    'keyboard-nav', 'navbar-menu', 'page-actions', 'search', 'sidebar-nav', 'sidebar-state',
}
PANE_RUNS = {
    'action-registry', 'appearance', 'asset-list', 'authored-a11y', 'base', 'blog-gallery',
    'clipboard', 'code-block', 'content-components', 'dark-mode', 'diagram', 'drawio', 'expo',
    'expo-geometry', 'filetree', 'image-zoom', 'landing', 'markmap', 'mermaid', 'palette-model',
    'plantuml', 'plantuml-browser', 'search-engine', 'surface-coordinator', 'swagger-init',
    'table-reader', 'tabs',
}
HOST_ONLY = {'compare-scroll', 'document-compare'}
# Every visible reader string is localized in Hugo and handed to the runtime.
READER_LABELS = {'title', 'sync', 'approximate', 'progress', 'unavailable', 'error', 'loading', 'retry', 'close', 'open', 'language'}
PANE_GUARD = re.compile(r"if \((?:typeof window !== 'undefined' && )?window\.OinkComparePane[^)]*\) return;")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def manifest(html: str):
    match = re.search(r'<script[^>]+id="td-compare-config"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(match.group(1)) if match else None


def check_pane_guards(errors: list[str]) -> None:
    runtimes = {path.stem: path.read_text(encoding='utf-8') for path in (ROOT / 'assets/js').glob('*.js')}
    classified = PANE_SUPPRESSED | PANE_RUNS | HOST_ONLY
    for name in sorted(set(runtimes) - classified):
        errors.append(f'assets/js/{name}.js is not classified for comparison panes in bin/check-compare.py')
    for name in sorted(classified - set(runtimes)):
        errors.append(f'bin/check-compare.py classifies missing runtime assets/js/{name}.js')
    # The entry's glyph must differ from every shell control's: Font Awesome
    # aliases (fa-columns is fa-table-columns) otherwise put two identical
    # icons with different actions on one screen.
    css = (ROOT / 'assets/third_party/Font-Awesome/css/fontawesome.css').read_text(encoding='utf-8')
    glyphs = dict(re.findall(r'\.fa-([a-z0-9-]+) \{\s*--fa: "([^"]+)"', css))
    entry_icons = re.findall(r'fa-solid fa-([a-z0-9-]+)', (ROOT / 'layouts/_partials/compare/entry.html').read_text(encoding='utf-8'))
    shell_icons = re.findall(r'fa-(?:solid|regular|brands) fa-([a-z0-9-]+)', (ROOT / 'layouts/_partials/shell/icon.html').read_text(encoding='utf-8'))
    require(bool(entry_icons), 'layouts/_partials/compare/entry.html has no Font Awesome icon', errors)
    for icon in entry_icons:
        clashes = sorted(name for name in shell_icons if glyphs.get(name) and glyphs.get(name) == glyphs.get(icon))
        require(icon in glyphs, f'compare entry icon fa-{icon} is not in the vendored Font Awesome', errors)
        require(not clashes, f'compare entry icon fa-{icon} draws the same glyph as shell icon(s) {clashes}', errors)
    # The reader must remeasure on the event OINK tabs actually dispatch:
    # equal-height panels change visible headings without resizing the article.
    tab_events = set(re.findall(r"new CustomEvent\('(td:tab-[a-z-]+)'", runtimes.get('tabs', '')))
    for event in sorted(tab_events):
        require(f"'{event}'" in runtimes.get('document-compare', ''),
                f'assets/js/document-compare.js must remeasure on {event} from assets/js/tabs.js', errors)
    require(bool(tab_events), 'assets/js/tabs.js no longer announces a td:tab-* event the reader can follow', errors)
    for name, source in runtimes.items():
        guarded = bool(PANE_GUARD.search(source))
        if name in PANE_SUPPRESSED:
            require(guarded, f'assets/js/{name}.js must stand down inside a comparison pane', errors)
        elif name in PANE_RUNS | HOST_ONLY:
            require(not guarded, f'assets/js/{name}.js must not stand down inside a comparison pane', errors)


def build(hugo: str, directory: Path, setting: str, *, cross_origin=False, zh_off=False, keyboard=True):
    config = [
        'baseURL: https://example.org/manual/', 'title: Compare fixture',
        f'theme: {ROOT.name}', 'defaultContentLanguage: en',
        'disableKinds: [RSS, sitemap, taxonomy, term]',
        'outputs:', '  section: [HTML, print]', '  page: [HTML, markdown]',
        'services:', '  googleAnalytics:', f'    ID: {GA_ID}',
        'languages:',
    ]
    for index, lang in enumerate(LANGUAGES):
        config += [f'  {lang}:', f'    weight: {index + 1}', f'    label: {lang}', f'    locale: {lang}', f'    contentDir: content/{lang}']
        if cross_origin:
            config.append(f'    baseURL: https://{"foreign.example.org" if lang == "de" else "example.org"}/{lang}/')
        if zh_off and lang == 'zh':
            config += ['    params:', '      ui:', '        compare: false']
    # One post per archive page, so the blog index paginates.
    params = ['    blog_index_size: 1']
    if setting:
        params.append(f'    compare: {setting}')
    if not keyboard:
        params.append('    keyboard_nav: false')
    if params:
        config += ['params:', '  ui:', *params]
    (directory / 'hugo.yaml').write_text('\n'.join(config) + '\n')
    for lang in LANGUAGES:
        root = directory / 'content' / lang
        for section, title in [('docs', 'Docs'), ('book', 'Book'), ('blog', 'Blog')]:
            (root / section).mkdir(parents=True)
            (root / section / '_index.md').write_text(f'---\ntitle: {title}\n---\n')
        body = '\n\n## First {#first}\n\nText.\n\n## Second {#second}\n\nText.\n'
        (root / 'docs/chapter.md').write_text('---\ntitle: Chapter\n---' + body)
        (root / 'book/chapter.md').write_text('---\ntitle: Book chapter\n---' + body)
        (root / 'blog/post.md').write_text('---\ntitle: Post\ndate: 2026-10-01\n---' + body)
        (root / 'blog/second.md').write_text('---\ntitle: Second post\ndate: 2026-09-01\n---' + body)
        # A link-only peer keeps a permalink but writes no HTML, directly or by cascade.
        (root / 'docs/link-peer.md').write_text('---\ntitle: Link peer\n' + ('build:\n  render: link\n' if lang == 'zh' else '') + '---\nText.\n')
        (root / 'docs/linked').mkdir()
        (root / 'docs/linked/_index.md').write_text('---\ntitle: Linked\n' + ('cascade:\n  build:\n    render: link\n' if lang == 'zh' else '') + '---\n')
        (root / 'docs/linked/child.md').write_text('---\ntitle: Linked child\n---\nText.\n')
        if lang == 'en':
            (root / 'docs/alone.md').write_text('---\ntitle: No translation\n---\n\nOnly English.\n')
            (root / 'docs/draft-peer.md').write_text('---\ntitle: Draft peer\n---\nText.\n')
            (root / 'docs/machine-peer.md').write_text('---\ntitle: Machine peer\n---\nText.\n')
        if lang == 'zh':
            (root / 'docs/draft-peer.md').write_text('---\ntitle: Draft\ndraft: true\n---\nText.\n')
            (root / 'docs/machine-peer.md').write_text('---\ntitle: Machine\noutputs: [markdown]\n---\nText.\n')
    result = run_hugo_process([hugo, '--source', str(directory), '--themesDir', str(ROOT.parent),
                              '--destination', str(directory / 'public'), '--buildDrafts', '--logLevel', 'warn'],
                             capture_output=True, text=True, check=False)
    log = result.stdout + result.stderr
    print(log, end='')
    if result.returncode != 0:
        raise SystemExit(f'Hugo failed for the comparison fixture:\n{log}')
    prefix = 'en/' if cross_origin else ''
    return directory / 'public', prefix, log


CASES = [
    # name, setting, enabled, options
    ('absent', '', False, {}),
    ('off', 'false', False, {}),
    ('on', 'true', True, {}),
    ('invalid', '{enable: true}', False, {}),
    ('cross-origin', 'true', True, {'cross_origin': True}),
    ('zh-off', 'true', True, {'zh_off': True}),
    ('no-keyboard', 'true', True, {'keyboard': False}),
]


def check_case(hugo: str, name: str, setting: str, enabled: bool, options: dict, errors: list[str]) -> None:
    with tempfile.TemporaryDirectory(prefix=f'oink-compare-{name}-') as temp:
        public, prefix, log = build(hugo, Path(temp), setting, **options)
        expected = len(LANGUAGES) - 1 - (1 if options.get('cross_origin') or options.get('zh_off') else 0)
        for page in ['docs/chapter', 'book/chapter', 'blog/post']:
            html = (public / prefix / page / 'index.html').read_text()
            data = manifest(html)
            label = f'{name}: {page}'
            require(bool(data) == enabled, f'{label}: comparison manifest presence should be {enabled}', errors)
            require(('<meta name="oink-compare-page"' in html) == enabled, f'{label}: pane bootstrap presence should be {enabled}', errors)
            if not enabled:
                require('data-td-compare-open' not in html and 'compare-entry' not in html, f'{label}: disabled page emits a comparison entry', errors)
                continue
            targets = data['targets']
            require(len(targets) == expected, f'{label}: expected {expected} targets, got {len(targets)}', errors)
            require(all(target['url'] != data['current']['url'] for target in targets), f'{label}: the current page is its own target', errors)
            if options.get('zh_off'):
                require(not any(target['url'].startswith('/manual/zh/') for target in targets), f'{label}: a language with comparison off is still a target', errors)
            if not options.get('cross_origin'):
                require(all(target['url'].startswith('/manual/') for target in targets), f'{label}: target URLs lose the deployment subpath', errors)
            require('document-compare' in data['src'], f'{label}: manifest does not name the lazy reader runtime', errors)
            require(not re.search(r'<script[^>]+src="[^"]*document-compare', html), f'{label}: the reader runtime loads eagerly', errors)
            require('compare-entry' in html and 'data-td-compare-open' in html, f'{label}: entry or entry runtime missing', errors)
            keyboard = options.get('keyboard', True)
            # The reader closes on the key that opened it, only where that key exists.
            require(data.get('shortcut') == ('B' if keyboard else ''), f'{label}: reader toggle shortcut should follow keyboard navigation', errors)
            labels = data.get('labels', {})
            require(READER_LABELS <= set(labels) and all(labels[key] for key in READER_LABELS),
                    f'{label}: reader labels must all come from the catalog: {sorted(READER_LABELS - set(labels))}', errors)
            require(('aria-keyshortcuts="B"' in html) == keyboard, f'{label}: aria-keyshortcuts should follow keyboard navigation', errors)
            require(('<kbd>B</kbd>' in html) == keyboard, f'{label}: keyboard help B row should follow keyboard navigation', errors)
            # Production builds keep Hugo's GA policy but skip pane documents.
            require('window.OinkComparePane) return;' in html and GA_ID in html, f'{label}: analytics is not pane-aware', errors)
        if not enabled:
            html = (public / prefix / 'docs/chapter/index.html').read_text()
            require(f'gtag/js?id={GA_ID}' in html and 'OinkComparePane' not in html, f'{name}: disabled sites must keep Hugo\'s analytics template', errors)
        if enabled:
            for page in ['link-peer', 'linked/child']:
                peer = manifest((public / prefix / f'docs/{page}/index.html').read_text())
                require(peer is not None and not any('/zh/' in target['url'] for target in peer['targets']),
                        f'{name}: docs/{page} offers a link-only (build.render: link) translation', errors)
            first = (public / prefix / 'blog/index.html').read_text()
            later = (public / prefix / 'blog/page/2/index.html').read_text()
            require(manifest(first) is not None, f'{name}: the first blog archive page lost its comparison', errors)
            require(manifest(later) is None and 'data-td-compare-open' not in later and 'compare_translations' not in later and '<kbd>B</kbd>' not in later,
                    f'{name}: blog archive page 2 must not offer comparison of page 1', errors)
            for page in ['alone', 'draft-peer', 'machine-peer']:
                require(manifest((public / prefix / f'docs/{page}/index.html').read_text()) is None, f'{name}: docs/{page} must not offer comparison', errors)
            if options.get('zh_off'):
                zh = (public / 'zh/docs/chapter/index.html').read_text()
                require(manifest(zh) is None and 'oink-compare-page' not in zh, f'{name}: a language with comparison off emits the reader', errors)
            for page in public.rglob('*.html'):
                if '_print' in page.parts:
                    require(manifest(page.read_text()) is None, f'{name}: print output {page} carries comparison', errors)
            for page in public.rglob('*.md'):
                require('td-compare-config' not in page.read_text(), f'{name}: Markdown output {page} carries comparison', errors)
        if name == 'invalid':
            require('params.ui.compare must be a boolean' in log, f'{name}: invalid setting does not warn', errors)
        else:
            require(not theme_warnings(log), f'{name}: unexpected theme warnings: {theme_warnings(log)}', errors)
        print(f'Comparison output: {name} built')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hugo', default='hugo')
    args = parser.parse_args()
    errors: list[str] = []
    check_pane_guards(errors)
    for name, setting, enabled, options in CASES:
        check_case(args.hugo, name, setting, enabled, options, errors)
    if errors:
        print('Comparison checks failed:', file=sys.stderr)
        for error in errors:
            print(f'  {error}', file=sys.stderr)
        return 1
    print('Comparison discovery, pane isolation, Docs/Book/Blog, per-language opt-out, keyboard, analytics and outputs passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
