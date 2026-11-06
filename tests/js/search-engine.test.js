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

// Synonyms help discovery; a keyword-only match still describes the page.
const keywordPages = [
  {
    ref: '/zh/config/',
    title: 'Configuration',
    keywords: ['配置', 'params', 'defaults'],
    description: '查找站点参数的类型、默认值与用法。',
    excerpt: 'A shorter fallback.',
  },
  {
    ref: '/zh/fallback/',
    title: 'Fallback',
    keywords: '配置 params defaults',
    excerpt: 'Site settings and examples.',
  },
  { ref: '/zh/no-summary/', title: 'No summary', keywords: ['配置'] },
  {
    ref: '/zh/body/',
    title: 'Body match',
    keywords: ['配置'],
    body: '这里介绍配置步骤。',
    description: 'Read the guide.',
  },
];
const keywordResults = engineModule.create(keywordPages, lunr, 20).query('配置');
const excerpts = new Map(keywordResults.map(({ doc, excerpt }) => [doc.ref, excerpt]));
assert.equal(excerpts.get('/zh/config/'), keywordPages[0].description);
assert.equal(excerpts.get('/zh/fallback/'), keywordPages[1].excerpt);
assert.equal(excerpts.get('/zh/no-summary/'), '');
assert.equal(excerpts.get('/zh/body/'), '这里介绍配置步骤。');

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

// Coverage outranks boosts; contiguous phrases lead within complete matches.
const mixed = engineModule.create([
  { ref: '/zh/docs/phrase/', title: 'PostgreSQL 备份', root: 'docs', boost: 1 },
  { ref: '/zh/docs/cross/', title: 'PostgreSQL', body: '用物理备份恢复', root: 'docs', boost: 10 },
  { ref: '/zh/blog/partial/', title: 'PostgreSQL', root: 'blog', boost: 100 },
  { ref: '/zh/docs/pool/', title: '连接池', keywords: ['PgBouncer'], body: '设置超时参数' },
], lunr, 10);
assert.deepEqual(mixed.query('PostgreSQL 备份').map(r => r.doc.ref),
  ['/zh/docs/phrase/', '/zh/docs/cross/']);
assert.equal(mixed.query('连接池 超时')[0].doc.ref, '/zh/docs/pool/');
assert.deepEqual(engineModule.terms('PostgreSQL备份 --baseURL /pg/data shared_buffers pg_basebackup'),
  ['postgresql', '备份', '--baseurl', '/pg/data', 'shared_buffers', 'pg_basebackup']);
assert.deepEqual(engineModule.terms(String.raw`文档/搜索.md C:\pg\data サーバー`),
  ['文档/搜索.md', String.raw`c:\pg\data`, 'サーバー']);
assert.deepEqual(mixed.query('postgresql 备份', {root: 'blog'}).map(r => [r.doc.ref, r.partial, r.matched, r.total]),
  [['/zh/blog/partial/', true, 1, 2]]);
assert.equal(mixed.query('连接池 missingword')[0].partial, true);
assert.deepEqual(mixed.query('" + : * ?'), []);
assert.equal(mixed.query('ＰｏｓｔｇｒｅＳＱＬ 备份')[0].doc.ref, '/zh/docs/phrase/');

const intro = '简介 😀 no matching text. ';
const first = '重复标题 shared_buffers controls cache. ';
const second = '重复标题 pg_basebackup -D /pg/data --checkpoint=fast PostgreSQL 备份。';
const sectionDoc = { ref: '/preview/zh/docs/database/', title: 'Database', root: 'docs',
  body: intro + first + second, sections: [
    {id: '重复标题', title: '重复标题', start: Buffer.byteLength(intro)},
    {id: '重复标题-1&x', title: '重复标题', start: Buffer.byteLength(intro + first)},
  ] };
const technical = engineModule.create([sectionDoc,
  {ref: '/wrong/', title: 'sharedbuffers pgbasebackup checkpointfast'},
], lunr, 10);
for (const token of ['pg_basebackup', '/pg/data', '--checkpoint=fast']) {
  const hits = technical.query(token);
  assert.equal(hits.length, 1);
  assert.equal(hits[0].ref, '/preview/zh/docs/database/#' + encodeURIComponent('重复标题-1&x'));
  assert.ok(hits[0].excerpt.includes(token));
}
assert.equal(technical.query('shared_buffers')[0].ref, '/preview/zh/docs/database/#' + encodeURIComponent('重复标题'));
assert.equal(technical.query('PostgreSQL 备份')[0].ref, '/preview/zh/docs/database/#' + encodeURIComponent('重复标题-1&x'));
assert.equal(technical.query('shared_buffers pg_basebackup').length, 1, 'merge multiple sections of one page');
assert.equal(engineModule.create([sectionDoc, sectionDoc], lunr, 10).query('shared_buffers').length, 1, 'deduplicate legacy repeated page records');
assert.deepEqual(technical.query('shared_buffxrs'), [], 'never typo-expand technical identifiers');
assert.ok(technical.query('shared').some(r => r.doc.ref === sectionDoc.ref), 'literal substrings still work');
const english = engineModule.create([{ref:'/en/', title:'Running database servers'}], lunr, 10);
assert.equal(english.query('run')[0].doc.ref, '/en/', 'English stemming');
assert.equal(english.query('databsae')[0].doc.ref, '/en/', 'bounded English typo fallback');
const inflected = engineModule.create([
  {ref:'/body/', body:'running'}, {ref:'/keyword/', keywords:['running']},
], lunr, 10);
assert.deepEqual(inflected.query('runs').map(r=>r.doc.ref), ['/keyword/', '/body/'],
  'English stem matches retain field weights');

const headingsOnly = engineModule.create([{ref:'/heading/', title:'Manual',
  headings:'连接设置', sections:[{id:'connection', title:'连接设置'}]}], lunr, 10);
assert.equal(headingsOnly.query('连接')[0].ref, '/heading/#connection');

// Search normalization must also locate excerpts and marks in the original text.
for (const [query, original] of [
  ['postgresql', 'ＰｏｓｔｇｒｅＳＱＬ'], ['café', 'cafe\u0301'],
  ['ffi', 'ﬃ'], ['가', '\u1100\u1161'],
]) {
  const text = '🙂 '.repeat(60) + original + ' backup';
  const hit = engineModule.create([{ref:'/unicode/', title:'Manual', body:text,
    sections:[{id:'unicode',title:'Details',start:0}]}], lunr).query(query)[0];
  assert.ok(hit.excerpt.includes(original), `normalized excerpt for ${query}`);
  assert.equal(hit.ref, '/unicode/#unicode');
  const ranges = engineModule.matchRanges(text, engineModule.terms(query));
  assert.deepEqual(ranges.map(([start,end])=>text.slice(start,end)), [original]);
}
assert.deepEqual(engineModule.matchRanges('Database database', ['data','database']), [[0,8],[9,17]]);
const scopedTypo = engineModule.create([
  {ref:'/blog/typo/', root:'blog', title:'databsae'},
  {ref:'/docs/database/', root:'docs', title:'database'},
], lunr);
assert.equal(scopedTypo.query('databsae', {root:'docs'})[0].doc.ref, '/docs/database/',
  'another root must not suppress spelling fallback inside the chosen scope');

// Issue #60: an identifier that skips Lunr (`top_k`) must rank the page that
// uses it repeatedly above a passing mention, not fall back to title order.
const identifier = engineModule.create([
  { ref: '/a/', title: 'Alpha notes', body: 'Benchmarks ran with top_k set to 10.' },
  { ref: '/q/', title: 'Query reference',
    body: 'top_k: number of results. Set top_k to 5 for short answers. top_k must be ' +
      'between 1 and 100. When top_k exceeds the candidate pool, fewer results return.' },
], null, 10);
assert.deepEqual(identifier.query('top_k').map((result) => result.doc.title),
  ['Query reference', 'Alpha notes']);
assert.equal(identifier.query('top_k').find((result) => result.doc.ref === '/a/').textScore, 10,
  'a single occurrence keeps the plain field weight');
// The same holds for a plain word that Lunr also matches.
const repeated = engineModule.create([
  { ref: '/a/', title: 'Alpha', body: 'One replica.' },
  { ref: '/z/', title: 'Zulu', body: 'A replica, its replica lag and a third replica.' },
], lunr, 10);
assert.deepEqual(repeated.query('replica').map((result) => result.doc.ref), ['/z/', '/a/']);
// Repetition reorders within a field tier but never crosses into the next.
const tiers = engineModule.create([
  { ref: '/body/', title: 'Body', body: Array(50).fill('top_k').join(' ') },
  { ref: '/description/', title: 'Zeta', description: 'Mentions top_k once.' },
  { ref: '/headings/', title: 'Headings', headings: Array(50).fill('top_k').join(' ') },
  { ref: '/tags/', title: 'Tags', tags: ['top_k'] },
], null, 10);
assert.deepEqual(tiers.query('top_k').map((result) => result.doc.ref),
  ['/tags/', '/headings/', '/description/', '/body/']);

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
