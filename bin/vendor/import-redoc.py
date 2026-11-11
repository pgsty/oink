#!/usr/bin/env python3
"""Inline ReDoc's two brand images so its default UI needs no CDN request.

Usage: python3 bin/vendor/import-redoc.py /outside/repo/redoc/package output.js
The input must be the original npm bundle. No network or package install runs.
"""
import base64
from pathlib import Path
import sys

package, output = map(Path, sys.argv[1:])
text = (package / 'bundles/redoc.standalone.js').read_text()
for name in ('logo-mini.svg', 'logo-mini-full.svg'):
    url = 'https://cdn.redoc.ly/redoc/' + name
    assert text.count(url) == 1, f'Review changed upstream image reference: {url}'
    image = (Path(__file__).parent / 'redoc-logos' / name).read_bytes()
    text = text.replace(url, 'data:image/svg+xml;base64,' + base64.b64encode(image).decode())
output.write_text(text)
