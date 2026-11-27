#!/usr/bin/env python3
"""Exercise Expo resource/output contracts and rejected author inputs in a fresh site."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import tempfile
import zlib
from test_site import ROOT, run_hugo_process


def png(width, height):
    def chunk(kind, data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    pixels=b''.join(b'\x00'+bytes([40,120,170])*width for _ in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b'')


def animated_gif():
    # Two 1x1 palette frames. Source bytes stay in the checker, not in Git assets.
    return bytes.fromhex('474946383961010001008000002878aaeeddbb21ff0b4e45545343415045322e30030100000021f904000a0000002c000000000100010000020244010021f904000a0000002c00000000010001000002024c01003b')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--hugo',default='hugo');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='oink-expo-') as tmp:
        site=Path(tmp);album=site/'content/expo/album';images=album/'images';images.mkdir(parents=True)
        (images/'small.png').write_bytes(png(160,100));(images/'long.png').write_bytes(png(200,2000));(images/'motion.gif').write_bytes(animated_gif())
        (site/'hugo.yaml').write_text('''baseURL: https://example.org/
title: Expo contract
theme: oink
defaultContentLanguage: en
languages:
  en: {weight: 1, locale: en-US}
  zh: {weight: 2, locale: zh-CN}
  ar: {weight: 3, locale: ar, direction: rtl}
outputs:
  home: [HTML, LLMS]
  section: [HTML, print, markdown, RSS]
  page: [HTML, markdown]
''')
        (site/'content/expo/_index.md').write_text('---\ntitle: Albums\nweight: 2\ncascade:\n  type: expo\noutputs: [HTML, print, markdown, RSS, LLMSFULL]\n---\n')
        (site/'content/expo/_index.zh.md').write_text('---\ntitle: 相册\ncascade:\n  type: expo\n---\n')
        # A lighter top-level section must not become the album's root label.
        (site/'content/notes').mkdir();(site/'content/notes/_index.md').write_text('---\ntitle: Notes\nweight: 1\n---\n')
        front='''title: Album
expo: {mode: seamless, size: 200}
resources:
  - src: images/small.png
    title: 'Small <test> & image'
    params: {id: small, caption: 'A <script>plain</script> caption', alt: Small image, weight: -1}
'''
        def build(extra=''):
            (album/'index.md').write_text('---\n'+front+extra+'---\nAlbum body.\n')
            (album/'index.zh.md').write_text('---\ntitle: 相册内容\n---\n正文。\n')
            (album/'index.ar.md').write_text('---\ntitle: ألبوم\n---\n')
            return run_hugo_process([args.hugo,'--source',str(site),'--themesDir',str(ROOT.parent),'--destination',str(site/'public'),'--environment','development','--printPathWarnings'],cwd=ROOT,capture_output=True,text=True)
        result=build();assert result.returncode==0,result.stdout+result.stderr
        public=site/'public';html=(public/'expo/album/index.html').read_text();md=(public/'expo/album/index.md').read_text();printed=(public/'_print/expo/index.html').read_text();rss=(public/'expo/index.xml').read_text();llms=(public/'expo/llms-full.txt').read_text()
        assert html.count('data-td-expo-item ')==3
        assert 'id="img-small"' in html and 'data-td-expo-mode="seamless"' in html
        assert 'data-td-expo-viewer' in html and '/js/chunks/expo.js' in html
        runtime=(public/'js/chunks/expo.js').read_text()
        assert re.search(r"\.register\(['\"]expo-viewer['\"]",runtime), 'Expo must register its coordinated close callback'
        assert html.count('name="td-expo-mode"')==3
        assert '<fieldset class="td-expo-modes"' in html and 'aria-keyshortcuts=";"' in html and 'type="range"' in html and ('aria-keyshortcuts=", . &lt; &gt;"' in html or 'aria-keyshortcuts=", . < >"' in html)
        assert 'data-td-expo-expand' in html and 'td-appearance-expo' not in html
        assert 'aria-keyshortcuts="W A S D"' in html and 'draggable="false"' in html
        assert 'aria-keyshortcuts="Q H ArrowLeft"' in html and 'aria-keyshortcuts="R 0"' in html
        assert 'class="td-page-actions' not in html
        assert re.search(r'class="td-shell-root__title">Albums<',html), 'Expo albums must use their section as sidebar root'
        assert 'data-td-expo-animated="true"' in html
        assert re.search(r'<img[^>]+src="[^"]+motion.gif"',html), 'GIF must play by default'
        assert 'prefers-reduced-motion: reduce' in html
        assert '&lt;script&gt;plain&lt;/script&gt;' in html and '<script>plain</script>' not in html
        zh=(public/'zh/expo/album/index.html').read_text()
        assert 'aria-label="展墙"' in zh and 'aria-label="上一张"' in zh and 'aria-label="下一张"' in zh, 'viewer steps name images, not pages'
        # The grid mirrors in RTL, so the arrow toward the start means previous.
        rtl=(public/'ar/expo/album/index.html').read_text()
        assert 'aria-keyshortcuts="Q H ArrowRight"' in rtl and 'aria-keyshortcuts="E L ArrowLeft"' in rtl
        assert 'aria-keyshortcuts="E L ArrowRight"' in html
        assert html.index('id="img-small"')<html.index('data-td-expo-animated="true"')
        for output in [md,llms]:
            assert '/expo/album/images/small.png' in output and '![Small image]' in output
            assert 'data-td-expo' not in output and '<dialog' not in output
            assert 'Album body.\n\n## ' in output, 'album prose must stay separate from image headings'
        assert 'img-small' in printed and 'data-td-expo-viewer' not in printed and 'js/chunks/expo' not in printed
        assert '/expo/album/images/small.png' in rss and 'data-td-expo-viewer' not in rss
        assert 'data-td-expo-viewer' not in (public/'index.html').read_text()
        for extra,warning in [('expo: {mode: wrong}\n','expo.mode'),('expo: {size: 12}\n','expo.size'),('expo: []\n','expo must be a map')]:
            original=front;front='title: Invalid\n'
            result=build(extra);assert result.returncode==0 and warning in result.stdout+result.stderr,(extra,result.stdout+result.stderr)
            front=original
        original=front
        for params,warning in [('original: missing.jpg','must name a bundled image'),('original: false','must name a bundled image'),('id: "invalid id"','id must contain'),('id: false','id must contain'),('caption: [bad]','must be a string'),('weight: nope','not a number')]:
            front='title: Invalid metadata\nresources:\n  - src: images/small.png\n    params: {'+params+'}\n'
            result=build();assert result.returncode==0 and warning in result.stdout+result.stderr,(params,result.stdout+result.stderr)
        front='title: Fallback\n'
        result=build('expo: {mode: wrong}\n');assert result.returncode==0,result.stdout+result.stderr
        result=build('expo: {images: false}\n');assert result.returncode==0 and 'expo.images' in result.stdout+result.stderr
        front='title: Integer ID\nresources:\n  - src: images/small.png\n    params: {id: 101}\n'
        result=build();assert result.returncode==0,result.stdout+result.stderr
        assert 'id="img-101"' in (public/'expo/album/index.html').read_text()
        # Authored IDs can occupy both a later filename hash and its suffixes.
        # Builds warn and still emit unique fallback anchors.
        for name in ('a', 'b', 'c', 'd'):
            (images/f'{name}.png').write_bytes(png(20,20))
        hashed=hashlib.sha256(b'images/d.png').hexdigest()[:16]
        front='title: Collisions\nresources:\n'
        for name,ident in zip(('a','b','c','d'),(hashed,hashed+'-1',hashed+'-3',hashed)):
            front+=f'  - src: images/{name}.png\n    params: {{id: "{ident}"}}\n'
        result=build();assert result.returncode==0 and 'duplicate image id' in result.stdout+result.stderr
        ids=re.findall(r'<figure\b[^>]*\bid="([^"]+)"', (public/'expo/album/index.html').read_text())
        assert len(ids)==7 and len(set(ids))==len(ids),ids
        assert f'img-{hashed}-2' in ids,ids
        print('Expo: outputs, metadata, integer IDs, collision-safe fallback and invalid-input gates passed')

if __name__=='__main__': main()
