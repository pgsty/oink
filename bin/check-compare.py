#!/usr/bin/env python3
"""Build small sites to check translation discovery, lazy assets and output isolation."""
from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path
from test_site import ROOT, run_hugo_process, theme_warnings


def manifest(html: str):
    match = re.search(r'<script[^>]+id="td-compare-config"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(match.group(1)) if match else None


def build(hugo: str, directory: Path, setting: str, cross_origin=False):
    languages = ['en', 'zh', 'de', 'ru', 'fr', 'es', 'ja', 'ar']
    config = [
        'baseURL: https://example.org/manual/', 'title: Compare fixture',
        f'theme: {ROOT.name}', 'defaultContentLanguage: en',
        'disableKinds: [RSS, sitemap, taxonomy, term]',
        'outputs:', '  section: [HTML, print]', '  page: [HTML, markdown]',
        'languages:',
    ]
    for index, lang in enumerate(languages):
        config += [f'  {lang}:', f'    weight: {index + 1}', f'    label: {lang}', f'    locale: {lang}', f'    contentDir: content/{lang}']
        if cross_origin:
            config.append(f'    baseURL: https://{"foreign.example.org" if lang == "de" else "example.org"}/{lang}/')
    if setting:
        config += ['params:', '  ui:', f'    compare: {setting}']
    (directory / 'hugo.yaml').write_text('\n'.join(config) + '\n')
    for lang in languages:
        content = directory / 'content' / lang / 'docs'
        content.mkdir(parents=True)
        (content / '_index.md').write_text('---\ntitle: Docs\n---\n')
        (content / 'chapter.md').write_text('---\ntitle: Chapter\n---\n\n## First {#first}\n\nText.\n\n## Second {#second}\n\nText.\n')
        if lang == 'en':
            (content / 'alone.md').write_text('---\ntitle: No translation\n---\n\nOnly English.\n')
            (content / 'draft-peer.md').write_text('---\ntitle: Draft peer\n---\nText.\n')
            (content / 'machine-peer.md').write_text('---\ntitle: Machine peer\n---\nText.\n')
        if lang == 'zh':
            (content / 'draft-peer.md').write_text('---\ntitle: Draft\ndraft: true\n---\nText.\n')
            (content / 'machine-peer.md').write_text('---\ntitle: Machine\noutputs: [markdown]\n---\nText.\n')
    result = run_hugo_process([hugo, '--source', str(directory), '--themesDir', str(ROOT.parent),
                              '--destination', str(directory / 'public'), '--buildDrafts', '--logLevel', 'warn'],
                             capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    print(result.stdout + result.stderr, end='')
    prefix = 'en/' if cross_origin else ''
    return directory / 'public', prefix, result.stdout + result.stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hugo', default='hugo')
    args = parser.parse_args()
    for name, setting, enabled, cross in [('absent', '', False, False), ('off', 'false', False, False),
                                           ('on', 'true', True, False), ('invalid', '{enable: true}', False, False),
                                           ('cross-origin', 'true', True, True)]:
        with tempfile.TemporaryDirectory(prefix=f'oink-compare-{name}-') as temp:
            public, prefix, log = build(args.hugo, Path(temp), setting, cross)
            html = (public / prefix / 'docs/chapter/index.html').read_text()
            data = manifest(html)
            assert bool(data) == enabled, name
            if enabled:
                assert len(data['targets']) == (6 if cross else 7), data
                assert all(target['url'] != data['current']['url'] for target in data['targets'])
                assert 'document-compare' in data['src']
                assert not re.search(r'<script[^>]+src="[^"]*document-compare', html)
                assert 'compare-entry' in html and 'data-td-compare-open' in html
                if not cross:
                    assert all(target['url'].startswith('/manual/') for target in data['targets'])
                for page in ['alone', 'draft-peer', 'machine-peer']:
                    assert manifest((public / prefix / f'docs/{page}/index.html').read_text()) is None, page
                for page in public.rglob('*.html'):
                    if '_print' in page.parts:
                        assert manifest(page.read_text()) is None, page
                for page in public.rglob('*.md'):
                    assert 'td-compare-config' not in page.read_text(), page
            else:
                assert 'data-td-compare-open' not in html and 'compare-entry' not in html
            if name == 'invalid':
                assert 'params.ui.compare must be a boolean' in log
            else:
                assert not theme_warnings(log), log
            print(f'Comparison output: {name} passed')
    print('Comparison discovery, lazy runtime, eight languages, subpaths and output isolation passed')


if __name__ == '__main__':
    main()
