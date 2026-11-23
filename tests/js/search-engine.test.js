'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

global.window = {};
const engineModule = require(
  path.join(__dirname, '..', '..', 'assets/js/search-engine.js'),
);
const refs = (results) => results.map((result) => result.doc.ref);

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

const engine = engineModule.create(documents, 20);

const latin = engine.query('pgboost');
assert.deepEqual(refs(latin).slice(0, 2), ['/docs/advanced/', '/docs/tutorial/']);
assert.ok(latin[0].score > latin[1].score);

const latinKeyword = engine.query('postgres');
assert.equal(latinKeyword[0].doc.ref, '/docs/reference/');
assert.ok(latinKeyword[0].score > 0);

const cjk = engine.query('增强词');
assert.deepEqual(refs(cjk).slice(0, 2), ['/zh/advanced/', '/zh/tutorial/']);
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
const keywordResults = engineModule.create(keywordPages, 20).query('配置');
const excerpts = new Map(keywordResults.map(({ doc, excerpt }) => [doc.ref, excerpt]));
assert.equal(excerpts.get('/zh/config/'), keywordPages[0].description);
assert.equal(excerpts.get('/zh/fallback/'), keywordPages[1].excerpt);
assert.equal(excerpts.get('/zh/no-summary/'), '');
assert.equal(excerpts.get('/zh/body/'), '这里介绍配置步骤。');

assert.deepEqual(refs(engine.query('tiequery')), ['/tie/a/', '/tie/b/']);

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
const scores = (pages) => engineModule.create(pages, 20).query('ordinary')
  .map((result) => [result.doc.ref, result.score]);
assert.deepEqual(scores(legacy), scores(defaults));

// Coverage outranks boosts. Among complete matches the fields that hold the
// query decide, scaled by the page boost and by an adjacent phrase.
const mixed = engineModule.create([
  { ref: '/zh/docs/phrase/', title: 'PostgreSQL 备份', root: 'docs', boost: 1 },
  { ref: '/zh/docs/cross/', title: 'PostgreSQL', body: '用物理备份恢复', root: 'docs', boost: 2 },
  { ref: '/zh/blog/partial/', title: 'PostgreSQL', root: 'blog', boost: 100 },
  { ref: '/zh/docs/pool/', title: '连接池', keywords: ['PgBouncer'], body: '设置超时参数' },
], 10);
assert.deepEqual(refs(mixed.query('PostgreSQL 备份')), ['/zh/docs/phrase/', '/zh/docs/cross/']);
assert.deepEqual(refs(mixed.query('PostgreSQL备份')), ['/zh/docs/phrase/', '/zh/docs/cross/'],
  'a missing space between scripts changes nothing');
assert.equal(mixed.query('PostgreSQL备份')[0].phrase, true);
assert.ok(mixed.query('PostgreSQL 备份')[0].strength > mixed.query('PostgreSQL 备份')[1].strength);
assert.equal(mixed.query('连接池 超时')[0].doc.ref, '/zh/docs/pool/');
assert.equal(mixed.query('连接池超时')[0].doc.ref, '/zh/docs/pool/', 'unspaced CJK query');
assert.equal(mixed.query('连接池超时')[0].partial, false,
  'a bigram that spans two words is not required of the page');
assert.deepEqual(engineModule.terms('PostgreSQL备份 --baseURL /pg/data shared_buffers pg_basebackup'),
  ['postgresql', '备份', '--baseurl', '/pg/data', 'shared_buffers', 'pg_basebackup']);
assert.deepEqual(engineModule.terms(String.raw`文档/搜索.md C:\pg\data サーバー`),
  ['文档/搜索.md', String.raw`c:\pg\data`, 'サー', 'ーバ', 'バー']);
assert.deepEqual(engineModule.terms('pg_upgrade升级 第3章 锁'),
  ['pg_upgrade', '升级', '第', '3', '章', '锁'], 'a letter or digit beside CJK starts a new piece');
assert.deepEqual(engineModule.terms('->> :: a + b "quoted". end.'), ['->>', '::', 'a', 'b', 'quoted', 'end']);
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
], 10);
for (const token of ['pg_basebackup', '/pg/data', '--checkpoint=fast']) {
  const hits = technical.query(token);
  assert.equal(hits.length, 1);
  assert.equal(hits[0].ref, '/preview/zh/docs/database/#' + encodeURIComponent('重复标题-1&x'));
  assert.ok(hits[0].excerpt.includes(token));
}
assert.equal(technical.query('shared_buffers')[0].ref, '/preview/zh/docs/database/#' + encodeURIComponent('重复标题'));
assert.equal(technical.query('PostgreSQL 备份')[0].ref, '/preview/zh/docs/database/#' + encodeURIComponent('重复标题-1&x'));
assert.equal(technical.query('shared_buffers pg_basebackup').length, 1, 'merge multiple sections of one page');
assert.equal(engineModule.create([sectionDoc, sectionDoc], 10).query('shared_buffers').length, 1, 'deduplicate legacy repeated page records');
assert.deepEqual(technical.query('shared_buffxrs'), [], 'never typo-expand technical identifiers');
assert.deepEqual(refs(technical.query('shared')), ['/wrong/', sectionDoc.ref],
  'a word matches inside an identifier; a title that begins with it still leads the body');
assert.equal(technical.query('simple').length, 0);
assert.equal(technical.query('简介')[0].ref, sectionDoc.ref, 'text before the first heading belongs to the page');

// One spelling path: a word, a longer word it begins, another inflection, a correction.
const english = engineModule.create([{ref:'/en/', title:'Running database servers'}], 10);
assert.equal(english.query('run')[0].doc.ref, '/en/', 'a word matches the words it begins');
assert.equal(english.query('databsae')[0].doc.ref, '/en/', 'bounded English typo fallback');
assert.deepEqual(english.query('databsae')[0].marks.map((mark) => mark.text), ['database'],
  'a correction is highlighted as the word that was found');
assert.deepEqual(english.query('dtabsae'), [], 'more than one slip in a short word is not corrected');
const inflected = engineModule.create([
  {ref:'/body/', body:'running'}, {ref:'/keyword/', keywords:['running']},
], 10);
assert.deepEqual(refs(inflected.query('runs')), ['/keyword/', '/body/'],
  'English stem matches retain field tiers');
assert.ok(inflected.query('runs')[0].marks.some((mark) => mark.text === 'running'));
for (const [word, stem] of [['caresses', 'caress'], ['ponies', 'poni'], ['agreed', 'agre'],
  ['hopping', 'hop'], ['filing', 'file'], ['happy', 'happi'], ['relational', 'relat'],
  ['adjustment', 'adjust'], ['replication', 'replic'], ['replicating', 'replic'],
  ['configuration', 'configur'], ['configure', 'configur'], ['sing', 'sing'], ['pg18', 'pg18']])
  assert.equal(engineModule.stem(word), stem, `stem of ${word}`);

// A short word never matches inside another word; a long one still finds a compound.
const boundary = engineModule.create([
  { ref: '/support/', title: 'Support matrix', body: 'Supported platforms and exports.' },
  { ref: '/port/', title: 'Networking', body: 'The default port is 5432; see listen_port.' },
  { ref: '/de/', title: 'Handbuch', body: 'Die Datenbankverbindung bleibt offen.' },
  { ref: '/ru/', title: 'Руководство', body: 'Настройка репликации базы данных.' },
], 10);
assert.deepEqual(refs(boundary.query('port')), ['/port/']);
assert.deepEqual(refs(boundary.query('verbindung')), ['/de/']);
assert.deepEqual(refs(boundary.query('репликация')), ['/ru/'], 'other alphabets match a differing ending');
assert.deepEqual(engineModule.matchRanges('Support the port', [{ text: 'port', word: true }]), [[12, 16]]);
assert.deepEqual(engineModule.matchRanges('Datenbankverbindung', [{ text: 'verbindung', word: true }]), [[9, 19]]);

// CJK runs match as overlapping bigrams; no dictionary and no language tag.
const han = engineModule.create([
  { ref: '/wal/', title: '可靠性', body: '预写式日志（WAL）保证事务提交后数据不会丢失。' },
  { ref: '/pool/', title: '连接', body: '连接池可以复用数据库连接，statement_timeout 用来限制语句超时。' },
  { ref: '/vacuum/', title: '日常维护', body: '自动清理守护进程会定期回收空间，可以按表配置。' },
  { ref: '/archive/', title: '归档', body: '配置 WAL 归档后才能做时间点恢复。' },
  { ref: '/ja/', title: 'レプリケーション', body: '論理レプリケーションの設定を説明します。' },
  { ref: '/ko/', title: '운영', body: '백업과 복구 절차를 설명합니다.' },
], 10);
assert.equal(han.query('预写日志')[0].doc.ref, '/wal/', 'wording that differs by one character');
assert.equal(han.query('预写日志')[0].partial, false);
assert.equal(han.query('数据库连接池超时')[0].doc.ref, '/pool/');
assert.equal(han.query('数据库连接池超时')[0].partial, false);
assert.equal(han.query('如何配置自动清理')[0].doc.ref, '/vacuum/');
assert.equal(han.query('如何配置自动清理')[0].partial, false, 'a question word is not required');
assert.deepEqual(refs(han.query('如何')), [], 'a question word alone is searched as written');
assert.equal(han.query('WAL归档')[0].doc.ref, '/archive/');
assert.deepEqual(refs(han.query('WAL归档')), refs(han.query('WAL 归档')));
assert.equal(han.query('レプリケーション設定')[0].doc.ref, '/ja/');
assert.equal(han.query('백업')[0].doc.ref, '/ko/', 'a Korean stem matches inside its inflected word');
assert.deepEqual(han.query('清理 没有的词').map((r) => [r.doc.ref, r.partial, r.matched, r.total]),
  [['/vacuum/', true, 1, 3]]);

// Operators and psql commands are literal.
const symbols = engineModule.create([
  { ref: '/json/', title: 'JSON operators', body: "data ->> 'name' extracts text; data -> 'name' keeps JSON." },
  { ref: '/psql/', title: 'psql', body: String.raw`Use \dt to list tables and \d+ for details.` },
], 10);
assert.deepEqual(refs(symbols.query('->>')), ['/json/']);
assert.deepEqual(refs(symbols.query(String.raw`\dt`)), ['/psql/']);

// A page's tier is the weakest field it needs to cover the whole query.
const ladder = engineModule.create([
  { ref: '/scattered/', title: 'Operations', body: 'intro', sections: [] },
  { ref: '/reindex/', title: 'REINDEX', body: 'You can create an index concurrently here too.' },
  { ref: '/create-index/', title: 'CREATE INDEX', body: 'Synopsis text. Building Indexes Concurrently Details here.',
    sections: [{ id: 'synopsis', title: 'Synopsis', start: 0 },
      { id: 'concurrently', title: 'Building Indexes Concurrently', start: 15 }] },
], 10);
const built = ladder.query('create index concurrently');
assert.deepEqual(refs(built), ['/create-index/', '/reindex/']);
assert.equal(built[0].ref, '/create-index/#concurrently', 'page title and section heading cover the query together');
const split = engineModule.create([
  { ref: '/one/', title: 'One', body: 'alpha here. beta there.',
    sections: [{ id: 'a', title: 'First', start: 0 }, { id: 'b', title: 'Second', start: 12 }] },
  { ref: '/two/', title: 'Two', body: 'alpha and beta together.' },
], 10);
assert.deepEqual(refs(split.query('alpha beta')), ['/two/', '/one/'],
  'one section that covers the query leads a page that needs two');
assert.equal(split.query('alpha beta')[1].partial, false);

const headingsOnly = engineModule.create([{ref:'/heading/', title:'Manual',
  description:'Connection guide.',
  headings:'连接设置', sections:[{id:'connection', title:'连接设置'}]}], 10);
assert.equal(headingsOnly.query('连接')[0].ref, '/heading/#connection');
assert.equal(headingsOnly.query('连接')[0].heading, '连接设置');
assert.equal(headingsOnly.query('连接')[0].excerpt, 'Connection guide.',
  'heading match without section body falls back to page description instead of duplicating heading');
assert.deepEqual(engineModule.matchRanges('Database', []), []);

// Search normalization must also locate excerpts and marks in the original text.
for (const [query, original] of [
  ['postgresql', 'ＰｏｓｔｇｒｅＳＱＬ'], ['café', 'cafe\u0301'],
  ['ffi', 'ﬃ'], ['가', '\u1100\u1161'],
]) {
  for (const padding of [60, 3000]) {
    const text = '🙂 '.repeat(padding) + original + ' backup';
    const hit = engineModule.create([{ref:'/unicode/', title:'Manual', body:text,
      sections:[{id:'unicode',title:'Details',start:0}]}]).query(query)[0];
    assert.ok(hit.excerpt.includes(original), `normalized excerpt for ${query} after ${padding}`);
    assert.equal(hit.ref, '/unicode/#unicode');
    const ranges = engineModule.matchRanges(text, engineModule.terms(query));
    assert.deepEqual(ranges.map(([start,end])=>text.slice(start,end)), [original]);
  }
}
assert.deepEqual(engineModule.matchRanges('Database database', ['data','database']), [[0,8],[9,17]]);
const scopedTypo = engineModule.create([
  {ref:'/blog/typo/', root:'blog', title:'databsae'},
  {ref:'/docs/database/', root:'docs', title:'database'},
]);
assert.equal(scopedTypo.query('databsae', {root:'docs'})[0].doc.ref, '/docs/database/',
  'another root must not suppress spelling fallback inside the chosen scope');

// Issue #60: the page that uses an identifier repeatedly ranks above a
// passing mention, instead of falling back to title order.
const identifier = engineModule.create([
  { ref: '/a/', title: 'Alpha notes', body: 'Benchmarks ran with top_k set to 10.' },
  { ref: '/q/', title: 'Query reference',
    body: 'top_k: number of results. Set top_k to 5 for short answers. top_k must be ' +
      'between 1 and 100. When top_k exceeds the candidate pool, fewer results return.' },
], 10);
assert.deepEqual(identifier.query('top_k').map((result) => result.doc.title),
  ['Query reference', 'Alpha notes']);
const repeated = engineModule.create([
  { ref: '/a/', title: 'Alpha', body: 'One replica.' },
  { ref: '/z/', title: 'Zulu', body: 'A replica, its replica lag and a third replica.' },
], 10);
assert.deepEqual(refs(repeated.query('replica')), ['/z/', '/a/']);
// Repetition reorders within a field tier but never crosses into the next.
const tiers = engineModule.create([
  { ref: '/body/', title: 'Body', body: Array(50).fill('top_k').join(' ') },
  { ref: '/description/', title: 'Zeta', description: 'Mentions top_k once.' },
  { ref: '/headings/', title: 'Headings', headings: Array(50).fill('top_k').join(' ') },
  { ref: '/tags/', title: 'Tags', tags: ['top_k'] },
], 10);
assert.deepEqual(refs(tiers.query('top_k')),
  ['/tags/', '/headings/', '/description/', '/body/']);
const boosted = engineModule.create([
  { ref: '/heading/', title: 'Guide', body: 'x', sections: [{ id: 'h', title: 'Replica lag', start: 0 }] },
  { ref: '/body/', title: 'Notes', body: 'About replica lag.', boost: 8 },
  { ref: '/phrase/', title: 'Other', body: 'The replica lag grows.' },
  { ref: '/apart/', title: 'Third', body: 'A replica. Later, some lag.' },
], 10);
assert.deepEqual(refs(boosted.query('replica lag')), ['/body/', '/heading/', '/phrase/', '/apart/'],
  'boost scales field strength; an adjacent phrase leads the same words apart');
// An identifier found whole leads the same text inside a longer name.
const names = engineModule.create([
  { ref: '/long/', title: 'Maintenance', body: 'maintenance_work_mem and autovacuum_work_mem.' },
  { ref: '/exact/', title: 'Memory', body: 'work_mem sets the base amount.' },
], 10);
assert.deepEqual(refs(names.query('work_mem')), ['/exact/', '/long/']);

// Function words in a spaced script are scored but never required.
const question = engineModule.create([
  { ref: '/vacuum/', title: 'Routine maintenance', body: 'Vacuum reclaims storage.' },
  { ref: '/howto/', title: 'How to read this manual', body: 'Conventions used in the text.' },
], 10);
assert.deepEqual(refs(question.query('how to vacuum')), ['/vacuum/']);
assert.equal(question.query('how to')[0].doc.ref, '/howto/');

if (process.argv.length > 2) {
  assert.equal(process.argv.length, 4, 'expected EN and ZH built index paths');
  const en = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const zh = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
  const enResults = engineModule.create(en, 20).query('pgboost');
  const zhResults = engineModule.create(zh, 20).query('增强词');
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
