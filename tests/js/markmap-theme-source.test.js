'use strict';

// Source contract only; rendered contrast and interactions belong to the
// sibling documentation site's Markmap browser suite.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const source = fs.readFileSync(
  path.join(__dirname, '../../assets/css/td/content-components.css'), 'utf8',
).replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, '');

test('Markmap maps the article token on screen with wrapper/SVG specificity', () => {
  assert.match(source,
    /@media\s+screen\s*\{\s*\.td-content\s+\.markmap\s*\{\s*--mm-text:\s*var\(--bs-body-color\);\s*--mm-bg:\s*var\(--bs-body-bg\);\s*--mm-link:\s*var\(--bs-link-color\);\s*\}\s*\}/,
    'keep the mapping screen-only and applicable to both wrapper and SVG');
});

test('Markmap has no competing text-token assignment or important override', () => {
  const declarations = source.match(/--mm-text\s*:[^;]+;/g) || [];
  assert.deepEqual(declarations, ['--mm-text: var(--bs-body-color);', '--mm-text: #000;']);
});
