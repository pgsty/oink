'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

global.window = {};
const lunr = require(
  path.join(__dirname, '..', '..', 'assets/js/third_party/lunr.min.js'),
);
const engineModule = require(
  path.join(__dirname, '..', '..', 'assets/js/search-engine.js'),
);

const documents = [
  {
    ref: '/docs/tutorial/',
    title: 'Tutorial',
    body: 'ordinary page',
    keywords: ['pgboost'],
    boost: 1.5,
  },
  {
    ref: '/docs/advanced/',
    title: 'Advanced',
    body: 'ordinary page',
    keywords: ['pgboost'],
    boost: 3,
  },
  {
    ref: '/docs/reference/',
    title: 'Reference',
    body: 'postgres appears in body',
    keywords: ['postgres'],
    boost: 1,
  },
  {
    ref: '/zh/tutorial/',
    title: '教程',
    body: '普通页面',
    keywords: ['增强词'],
    boost: 1.5,
  },
  {
    ref: '/zh/advanced/',
    title: '高级',
    body: '普通页面',
    keywords: ['增强词'],
    boost: 3,
  },
  {
    ref: '/tie/b/',
    title: 'Same',
    body: 'tiequery',
    keywords: [],
    boost: 1,
  },
  {
    ref: '/tie/a/',
    title: 'Same',
    body: 'tiequery',
    keywords: [],
    boost: 1,
  },
];

const engine = engineModule.create(documents, lunr, 20);

const latin = engine.queryLatin('pgboost');
assert.deepEqual(
  latin.slice(0, 2).map((result) => result.doc.ref),
  ['/docs/advanced/', '/docs/tutorial/'],
);
assert.ok(latin[0].score > latin[1].score);

const latinKeyword = engine.queryLatin('postgres');
assert.equal(latinKeyword[0].doc.ref, '/docs/reference/');
assert.ok(latinKeyword[0].score > 0);

const cjk = engine.queryCjk('增强词');
assert.deepEqual(
  cjk.slice(0, 2).map((result) => result.doc.ref),
  ['/zh/advanced/', '/zh/tutorial/'],
);
assert.equal(cjk[0].textScore, cjk[1].textScore);
assert.ok(cjk[0].score > cjk[1].score);

const tie = engine.queryLatin('tiequery');
assert.deepEqual(
  tie.map((result) => result.doc.ref),
  ['/tie/a/', '/tie/b/'],
);

const grouped = engineModule.group([
  { doc: { ref: '/docs/a/', root: 'Docs', breadcrumb: ['Documentation'] } },
  { doc: { ref: '/blog/a/', type: 'BLOG', breadcrumb: ['Blog'] } },
  { doc: { ref: '/docs/b/', root: 'docs', breadcrumb: ['Docs'] } },
]);
assert.deepEqual(
  grouped.map((group) => ({
    key: group.key,
    label: group.label,
    refs: group.results.map((result) => result.doc.ref),
  })),
  [
    {
      key: 'docs',
      label: 'Documentation',
      refs: ['/docs/a/', '/docs/b/'],
    },
    { key: 'blog', label: 'Blog', refs: ['/blog/a/'] },
  ],
);

const legacy = documents.map(({ keywords, boost, ...document }) => document);
const defaults = legacy.map((document) => ({
  ...document,
  keywords: [],
  boost: 1,
}));
const legacyResults = engineModule
  .create(legacy, lunr, 20)
  .queryLatin('ordinary')
  .map((result) => [result.doc.ref, result.score]);
const defaultResults = engineModule
  .create(defaults, lunr, 20)
  .queryLatin('ordinary')
  .map((result) => [result.doc.ref, result.score]);
assert.deepEqual(legacyResults, defaultResults);

if (process.argv.length > 2) {
  assert.equal(process.argv.length, 4, 'expected EN and ZH built index paths');
  const en = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const zh = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
  const enResults = engineModule.create(en, lunr, 20).queryLatin('pgboost');
  const zhResults = engineModule.create(zh, lunr, 20).queryCjk('增强词');
  assert.deepEqual(
    enResults.slice(0, 2).map((result) => result.doc.ref.split('/').at(-2)),
    ['advanced', 'tutorial'],
  );
  assert.deepEqual(
    zhResults.slice(0, 2).map((result) => result.doc.ref.split('/').at(-2)),
    ['advanced', 'tutorial'],
  );
}

console.log('search engine ranking checks passed');
