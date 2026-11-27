'use strict';

const assert = require('node:assert/strict');
const { test } = require('node:test');
const copy = require('../../assets/js/rich-copy.js');

// A DOM small enough to read: the walker only asks for these members.
function el(tag, attrs, ...kids) {
  const node = {
    nodeType: 1,
    nodeName: tag.toUpperCase(),
    attrs: attrs || {},
    childNodes: kids.map(kid => (typeof kid === 'string' ? { nodeType: 3, nodeValue: kid } : kid)),
    getAttribute(name) { return name in this.attrs ? this.attrs[name] : null; },
    hasAttribute(name) { return name in this.attrs; },
    classList: { contains: name => String((attrs || {}).class || '').split(/\s+/).includes(name) },
  };
  node.childNodes.forEach(kid => { kid.parentNode = node; });
  if (node.attrs.href) node.href = node.attrs.href;
  if (node.attrs.src) node.src = node.attrs.src;
  return node;
}

const paper = copy.readSkin({
  getPropertyValue(name) {
    return ({
      '--td-print-ink': '#1f1e1c', '--td-print-strong': '#141413', '--td-print-link': ' #2B5F8C ',
      '--td-print-quote-line': 'rgb(155, 74, 40)', '--td-print-header-bg': 'url(javascript:alert(1))',
      '--td-code-radius': '12px', '--td-copy-heading-rule': 'over', '--td-copy-heading-font': '"Plex Mono", monospace',
    })[name] || '';
  },
}, 'ltr');

function typeset(root, env) {
  return copy.render(copy.collector(null, env || {}).walk(root), paper);
}

test('colours travel as hex or rgba and nothing else', () => {
  assert.equal(copy.color('rgb(247, 246, 243)'), '#f7f6f3');
  assert.equal(copy.color('rgba(33, 32, 28, 0.06)'), 'rgba(33, 32, 28, 0.06)');
  assert.equal(copy.color('color(srgb 1 0.5 0 / 0.5)'), 'rgba(255, 128, 0, 0.5)');
  assert.equal(copy.color('rgba(0, 0, 0, 0)'), '');
  assert.equal(copy.color('red; background: url(x)'), '');
  assert.equal(paper.link, '#2b5f8c');
  assert.equal(paper.quoteLine, '#9b4a28');
  assert.equal(paper.headerBg, '#edf0f3', 'an unusable token keeps the default');
  assert.equal(paper.radius, 8, 'the corner is capped for a pasted block');
  assert.equal(paper.headingFont, "'Plex Mono', monospace");
});

test('a document carries no canvas and no interface', () => {
  const html = typeset(el('div', { class: 'td-content' },
    el('div', { class: 'td-page-heading' }, el('h1', null, 'Title')),
    el('header', { class: 'td-article-meta' }, el('p', null, '2 minutes')),
    el('h2', { id: 'why' }, 'Why', el('a', { class: 'td-heading-self-link', href: 'https://example.org/#why' })),
    el('p', null, 'Read the ', el('a', { href: 'https://example.org/docs/' }, 'guide'), ' or run ', el('code', null, 'hugo'), '.'),
    el('p', null, el('a', { href: 'javascript:alert(1)' }, 'unsafe')),
    el('div', { class: 'td-page-end' }, el('nav', null, 'Next page'))));
  assert.match(html, /^<h1 style="margin:0px 0 20px;[^"]*color:#141413;[^"]*">Title<\/h1>/);
  assert.match(html, /<h2 style="[^"]*border-top:1px solid #141413;[^"]*font-family:'Plex Mono', monospace;">Why<\/h2>/);
  assert.match(html, /<a href="https:\/\/example\.org\/docs\/" style="color:#2b5f8c;text-decoration:underline;">guide<\/a>/);
  assert.match(html, /<code style="[^"]*">hugo<\/code>\.<\/p>/);
  assert.match(html, />unsafe<\/p>/);
  assert.doesNotMatch(html, /javascript:|2 minutes|Next page|td-|background(?:-color)?:(?!#edf0f3)/);
});

test('a source line break between wide characters is not a space', () => {
  const html = typeset(el('div', { class: 'td-content' },
    el('p', null, '字体角色，\n中文与 English\n混排\n', el('strong', null, '加粗'), '\nend of line\nnext'),
    el('p', null, 'a')));
  assert.match(html, />字体角色，中文与 English 混排<strong[^>]*>加粗<\/strong> end of line next<\/p>/);
});

test('a phrase inside one block travels bare', () => {
  assert.equal(typeset(el('p', null, '  some ', el('strong', null, 'bold'), ' text ')), 'some <strong>bold</strong> text');
  assert.equal(typeset(el('ul', null, el('li', null, 'one ', el('em', null, 'item')))), 'one <em>item</em>');
});

test('a partial ordered list keeps the numbers the reader selected', () => {
  const first = el('li', null, 'First');
  const list = el('ol', { start: '0' }, first, el('li', null, 'Second'), el('li', { value: '8' }, 'Eighth'));
  assert.match(typeset(list), /^<ol start="0".*<li value="8"/);
  list.attrs.reversed = '';
  delete list.attrs.start;
  const range = { intersectsNode: node => node !== first };
  const html = copy.render(copy.collector(range, {}).walk(list), paper);
  assert.match(html, /^<ol start="2" reversed.*>Second<\/li><li value="8"/);
  assert.doesNotMatch(html, /First/);
  delete list.attrs.reversed;
  assert.match(copy.render(copy.collector(range, {}).walk(list), paper), /^<ol start="2"/);
});

test('lists, quotes, callouts and tables keep their structure', () => {
  const html = typeset(el('div', { class: 'td-content' },
    el('ol', { start: '3' }, el('li', null, el('p', null, 'loose')), el('li', null, 'outer', el('ul', null, el('li', null, 'inner')))),
    el('blockquote', null, el('p', null, 'quoted')),
    el('details', { class: 'td-callout td-callout--note' },
      el('summary', { class: 'td-callout__title' }, el('i', { class: 'fa-solid fa-circle-info', 'aria-hidden': 'true' }), el('span', { class: 'td-callout__label' }, 'Note')),
      el('div', { class: 'td-callout__body' }, el('p', null, 'folded away'))),
    el('table', null,
      el('thead', null, el('tr', null, el('th', null, 'Key'), el('th', { align: 'right' }, 'Value'))),
      el('tbody', null, el('tr', null, el('td', { colspan: '2' }, 'wide'))))));
  assert.match(html, /<ol start="3" style="[^"]*padding-left:28px;[^"]*"><li style="margin:0 0 6px;">loose<\/li><li style="margin:0 0 6px;">outer<ul style="margin:6px 0 0;/);
  assert.match(html, /<blockquote style="[^"]*border-left:3px solid #9b4a28;[^"]*"><p style="margin:0px 0 8px;[^"]*">quoted<\/p><\/blockquote>/);
  assert.match(html, /<blockquote[^>]*><p[^>]*font-weight:700[^>]*>Note<\/p><\/blockquote>/);
  assert.doesNotMatch(html, /folded away/, 'a closed disclosure copies its title only');
  assert.match(html, /<th style="[^"]*text-align:left;[^"]*font-weight:700;">Key<\/th><th style="[^"]*text-align:right;/);
  assert.match(html, /<td colspan="2" style="[^"]*">wide<\/td>/);
});

test('code keeps its text and token ink, and drops line numbers', () => {
  const inks = new Map();
  const ink = (node, style) => { inks.set(node, style); return node; };
  const keyword = ink(el('span', { class: 'k' }, 'func'), { color: 'rgb(207, 34, 46)', fontWeight: '400', fontStyle: 'normal' });
  const comment = ink(el('span', { class: 'c1' }, '// <note>'), { color: 'rgb(87, 96, 106)', fontWeight: '400', fontStyle: 'italic' });
  const pre = ink(el('pre', { class: 'chroma' }, el('code', { 'data-lang': 'go' },
    el('span', { class: 'line' }, el('span', { class: 'ln' }, '1'), keyword, ' main() {\n'),
    el('span', { class: 'line' }, el('span', { class: 'ln' }, '2'), '\t', comment, '\n'))),
    { backgroundColor: 'rgba(0, 0, 0, 0)', color: 'rgb(31, 30, 28)' });
  const shell = ink(el('div', { class: 'td-code' },
    el('div', { class: 'td-code__header' }, el('span', { class: 'td-code__filename' }, 'main.go'),
      el('div', { class: 'td-code__utilities' }, el('button', null, 'Copy'))),
    el('div', { class: 'highlight' }, pre)), { backgroundColor: 'rgb(255, 255, 255)' });
  const env = { styleOf: node => inks.get(node) || null };
  const light = typeset(el('div', { class: 'td-content' }, el('p', null, 'Run:'), shell), env);
  assert.match(light, /<p style="[^"]*border-radius:8px 8px 0 0;[^"]*">main\.go<\/p><pre style="[^"]*background:#f5f7f9;[^"]*white-space:pre;[^"]*"><code class="language-go"/);
  assert.match(light, /<span style="color:#cf222e;">func<\/span> main\(\) \{\n\t<span style="color:#57606a;font-style:italic;">\/\/ &lt;note&gt;<\/span><\/code><\/pre>$/);
  assert.doesNotMatch(light, /Copy|>1<|>2</);

  inks.set(shell, { backgroundColor: 'rgb(18, 17, 16)' });
  inks.set(pre, { backgroundColor: 'rgba(0, 0, 0, 0)', color: 'rgb(230, 225, 216)' });
  const dark = typeset(el('div', { class: 'td-content' }, el('p', null, 'Run:'), shell), env);
  assert.match(dark, /<pre style="[^"]*background:#121110;color:#e6e1d8;/, 'a dark code card travels as it is');
  assert.match(dark, /<p style="[^"]*color:#1f1e1c;">Run:<\/p>/, 'prose stays on the paper palette');

  assert.equal(typeset(el('pre', null, el('code', null, 'hugo server\n'))), '<code>hugo server</code>');
});

test('a zoomable image keeps its picture and loses its button', () => {
  const html = typeset(el('div', { class: 'td-content' },
    el('p', null, 'Before'),
    el('figure', null,
      el('button', { class: 'td-image-zoom__trigger', 'aria-label': 'Shell Open image' },
        el('img', { src: 'https://example.org/shell.webp', alt: 'Shell' })),
      el('figcaption', null, 'The shell')),
    el('p', null, el('button', { type: 'button' }, 'Copy'), el('img', { src: 'javascript:alert(1)', alt: 'bad' }))));
  assert.match(html, /<figure style="[^"]*text-align:center;"><img src="https:\/\/example\.org\/shell\.webp" alt="Shell" style="max-width:100%;height:auto;"><figcaption style="[^"]*">The shell<\/figcaption><\/figure>/);
  assert.doesNotMatch(html, /Open image|<button|Copy|javascript:/);
});

test('hidden content, icons and math sources', () => {
  const html = typeset(el('div', { class: 'td-content' },
    el('p', null, 'Seen', el('span', { hidden: '' }, ' never'), el('span', { class: 'visually-hidden' }, ' spoken'),
      el('i', { class: 'fa-solid fa-star' }), el('span', { class: 'gone' }, ' styled away')),
    el('p', null, 'Mass ', el('span', { class: 'katex' }, el('math', null, el('semantics', null, el('mrow', null, 'E'),
      el('annotation', { encoding: 'application/x-tex' }, 'E=mc^2'))))),
    el('ul', null, el('li', null, el('input', { type: 'checkbox' }), 'todo'))),
  { styleOf: node => (node.attrs && node.attrs.class === 'gone' ? { display: 'none' } : null) });
  assert.match(html, />Seen<\/p>/);
  assert.match(html, />Mass \$E=mc\^2\$<\/p>/);
  assert.match(html, /<li[^>]*>☐ todo<\/li>/);
});

test('a mounted map drops its interactive canvas and load button, keeping the place list', () => {
  const html = typeset(el('div', { class: 'td-content' },
    el('figure', { class: 'td-map td-map--interactive' },
      el('button', { class: 'td-map__load' }, 'Load map (tile.example.org)'),
      el('div', { class: 'td-map__canvas leaflet-container' },
        el('div', { class: 'leaflet-popup' }, el('p', null, 'Popup text')),
        el('div', { class: 'leaflet-control-attribution' }, '© OpenStreetMap contributors')),
      el('ol', { class: 'td-map__places' },
        el('li', null,
          el('span', { class: 'td-map__place' },
            el('span', { class: 'td-map__name' }, 'Kyoto Station'),
            ' ',
            el('a', { class: 'td-map__coords', href: 'https://www.openstreetmap.org/' }, '34.9858, 135.7589')),
          el('img', { class: 'td-map__thumb', src: 'https://example.org/kyoto.webp', alt: '' }))),
      el('figcaption', null, 'Kyoto'))));
  assert.match(html, /^<figure style="margin:0px 0 16px;text-align:left;">/);
  assert.match(html, /<ol[^>]*><li[^>]*>Kyoto Station <a[^>]*>34\.9858, 135\.7589<\/a><br><img src="https:\/\/example\.org\/kyoto\.webp" alt=""/);
  assert.match(html, /<figcaption[^>]*>Kyoto<\/figcaption>/);
  assert.doesNotMatch(html, /Popup text|OpenStreetMap contributors|Load map|text-align:center/);
});

test('a social post figure keeps start alignment and omits the decorative avatar image', () => {
  const html = typeset(el('div', { class: 'td-content' },
    el('figure', { class: 'td-social td-social--x' },
      el('figcaption', { class: 'td-social__author' },
        el('img', { class: 'td-social__avatar', src: 'https://example.org/avatar.webp', alt: '' }),
        el('span', { class: 'td-social__names' },
          el('span', { class: 'td-social__name' }, 'Alice'),
          ' ',
          el('span', { class: 'td-social__handle' }, '@alice'))),
      el('blockquote', { class: 'td-social__body' }, el('p', null, 'Shipped v1.7.')),
      el('p', { class: 'td-social__meta' },
        el('a', { href: 'https://x.com/alice/status/1' }, '2026-11-27 · View original')))));
  assert.match(html, /^<figure style="margin:0px 0 16px;text-align:left;">/);
  assert.match(html, /<figcaption[^>]*>Alice @alice<\/figcaption>/);
  assert.match(html, /Shipped v1\.7\./);
  assert.doesNotMatch(html, /avatar\.webp|text-align:center/);
});

test('update metadata copies as separated tokens instead of glued text', () => {
  const meta = el('div', { class: 'td-update-meta' },
    el('time', { datetime: '2026-11-23' }, '2026-11-23'),
    el('span', { class: 'td-update-sep' }, ', '),
    el('span', { class: 'td-update-tag' }, 'Breaking'),
    el('span', { class: 'td-update-sep' }, ', '),
    el('span', { class: 'td-update-tag' }, 'Performance'));
  const block = typeset(el('div', { class: 'td-content' },
    el('h2', { id: 'v1-6-0', class: 'update' }, 'v1.6.0'),
    '\n',
    meta,
    '\n',
    el('p', null, 'Body.'),
    el('h2', { id: 'v1-5-1', class: 'update' }, 'v1.5.1'),
    el('p', null, 'Older.')));
  assert.match(block, /<h2 style="margin:0px 0 6px;font-size:21px;[^"]*">v1\.6\.0<\/h2><p style="margin:0px 0 12px;font-size:13px;line-height:1\.6;color:#4e555c;"><span style="font-weight:600;color:#141413;">2026-11-23<\/span> <span style="padding:1px 6px;border:1px solid #c9ced4;border-radius:4px;color:#4e555c;font-size:12px;font-weight:600;">Breaking<\/span> <span style="padding:1px 6px;border:1px solid #c9ced4;border-radius:4px;color:#4e555c;font-size:12px;font-weight:600;">Performance<\/span><\/p><p/);
  assert.match(block, /<h2 style="margin:36px 0 16px;padding:16px 0 0;border-top:1px solid #141413;[^"]*">v1\.5\.1<\/h2>/);
  assert.doesNotMatch(block, /border-bottom:1px solid/);
  assert.doesNotMatch(block, /2026-11-23Breaking|BreakingPerformance/);
  assert.doesNotMatch(block, />,\s*<\/span>|td-update-sep/, 'separators are spacing, not chips');
  assert.equal(typeset(meta), '2026-11-23, Breaking, Performance');
});

test('an audio figure keeps its start alignment and hidden print URL link', () => {
  const url = el('p', { class: 'td-media__url' },
    el('a', { href: 'https://example.org/media/clip.mp3', rel: 'external' }, 'https://example.org/media/clip.mp3'));
  const figure = el('figure', { class: 'td-media td-media--audio' },
    el('figcaption', null,
      el('span', { class: 'td-media__title', id: 'td-audio-x-a0-title' }, 'Voice sample 1'),
      ' ',
      el('span', { class: 'td-fig-caption', id: 'td-audio-x-a0-caption' }, '440 Hz sine wave')),
    el('audio', { controls: '', src: 'https://example.org/media/clip.mp3' },
      el('a', { href: 'https://example.org/media/clip.mp3' }, 'Voice sample 1')),
    url);
  const env = { styleOf: node => (node === url ? { display: 'none' } : null) };
  const html = typeset(el('div', { class: 'td-content' }, figure), env);
  assert.match(html, /^<figure style="margin:0px 0 16px;text-align:left;"><figcaption[^>]*>Voice sample 1 440 Hz sine wave<\/figcaption><p[^>]*><a href="https:\/\/example\.org\/media\/clip\.mp3"[^>]*>https:\/\/example\.org\/media\/clip\.mp3<\/a><\/p><\/figure>$/);
  assert.doesNotMatch(html, /<audio/);

  const rtl = copy.render(copy.collector(null, env).walk(el('div', { class: 'td-content' }, figure)), { ...paper, rtl: true });
  assert.match(rtl, /^<figure style="margin:0px 0 16px;text-align:right;">/);
});

test('platform cards avoid duplicate URLs before click and keep the fallback URL after click', () => {
  const cardUrl = el('p', { class: 'td-media__url' },
    el('span', { class: 'td-media__url-title' }, 'Talk · Bilibili · '),
    el('a', { href: 'https://www.bilibili.com/video/BV1xx411c7mD', rel: 'external' }, 'https://www.bilibili.com/video/BV1xx411c7mD'));
  const unclicked = el('figure', { class: 'td-media td-media--embed' },
    el('a', { class: 'td-media-card', href: 'https://www.bilibili.com/video/BV1xx411c7mD', rel: 'external' },
      el('span', { class: 'td-media-card__play', 'aria-hidden': 'true' }, el('i', { class: 'fa-solid fa-play' })),
      el('span', { class: 'td-media-card__text' },
        el('span', { class: 'td-media-card__title' }, 'Talk'),
        el('span', { class: 'visually-hidden' }, ' · '),
        el('span', { class: 'td-media-card__platform' }, el('i', { class: 'fa-brands fa-bilibili', 'aria-hidden': 'true' }), ' Bilibili'))),
    cardUrl);
  const env = { styleOf: node => (node === cardUrl ? { display: 'none' } : null) };
  const beforeHtml = typeset(el('div', { class: 'td-content' }, unclicked), env);
  assert.equal((beforeHtml.match(/BV1xx411c7mD/g) || []).length, 1);

  const clickedUrl = el('p', { class: 'td-media__url' },
    el('span', { class: 'td-media__url-title' }, 'Talk · Bilibili · '),
    el('a', { href: 'https://www.bilibili.com/video/BV1xx411c7mD', rel: 'external' }, 'https://www.bilibili.com/video/BV1xx411c7mD'));
  const clicked = el('figure', { class: 'td-media td-media--embed' },
    el('div', { class: 'td-media-player' },
      el('iframe', { src: 'https://player.bilibili.com/player.html?bvid=BV1xx411c7mD&p=1&autoplay=1&danmaku=0', title: 'Talk' })),
    clickedUrl);
  const afterHtml = typeset(el('div', { class: 'td-content' }, clicked), { styleOf: node => (node === clickedUrl ? { display: 'none' } : null) });
  assert.match(afterHtml, /Talk · Bilibili · <a href="https:\/\/www\.bilibili\.com\/video\/BV1xx411c7mD"/);
  assert.doesNotMatch(afterHtml, /<iframe/);
});
