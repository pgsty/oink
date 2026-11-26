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
