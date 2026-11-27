'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');

global.__OINK_HISTORY_MANUAL_INIT__ = true;
const history = require(path.join(__dirname, '..', '..', 'assets/js/history.js'));

// A small DOM: enough selectors for the overlay, nothing more.
class Node {
  constructor(tag, attrs = {}) {
    this.tagName = tag.toUpperCase();
    this.nodeType = tag === '#text' ? 3 : 1;
    this.children = [];
    this.parentNode = null;
    this.attributes = new Map(Object.entries(attrs));
    this.listeners = new Map();
    this.hidden = false;
    this.disabled = false;
    this.value = '';
    this.text = '';
    this.offsetParent = {};
    this.ownerDocument = null;
    const node = this;
    const set = () => new Set(String(node.getAttribute('class') || '').split(/\s+/).filter(Boolean));
    this.classList = {
      add(...names) { const s = set(); names.forEach((n) => s.add(n)); node.setAttribute('class', [...s].join(' ')); },
      remove(...names) { const s = set(); names.forEach((n) => s.delete(n)); node.setAttribute('class', [...s].join(' ')); },
      contains(name) { return set().has(name); },
    };
  }
  set className(value) { this.setAttribute('class', value); }
  get className() { return this.getAttribute('class') || ''; }
  set id(value) { this.setAttribute('id', value); }
  get id() { return this.getAttribute('id') || ''; }
  get textContent() {
    return this.nodeType === 3 ? this.text : this.children.map((child) => child.textContent).join('');
  }
  set textContent(value) {
    if (this.nodeType === 3) { this.text = String(value); return; }
    this.children.forEach((child) => { child.parentNode = null; });
    this.children = [];
    if (value) this.appendChild(this.ownerDocument.createTextNode(value));
  }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.has(name) ? this.attributes.get(name) : null; }
  hasAttribute(name) { return this.attributes.has(name); }
  removeAttribute(name) { this.attributes.delete(name); }
  appendChild(child) {
    if (child.tagName === '#FRAGMENT') {
      child.children.slice().forEach((grand) => this.appendChild(grand));
      child.children = [];
      return child;
    }
    child.parentNode = this;
    child.ownerDocument = this.ownerDocument;
    this.children.push(child);
    return child;
  }
  addEventListener(type, fn) {
    this.listeners.set(type, (this.listeners.get(type) || []).concat(fn));
  }
  dispatch(type, values = {}) {
    const event = {
      type, target: this, key: '', shiftKey: false, metaKey: false, ctrlKey: false,
      preventDefault() { this.defaultPrevented = true; }, ...values,
    };
    (this.listeners.get(type) || []).forEach((fn) => fn(event));
    return event;
  }
  click() { this.dispatch('click'); }
  focus() { this.ownerDocument.activeElement = this; }
  blur() { if (this.ownerDocument && this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
  scrollIntoView() {}
  contains(node) {
    for (let current = node; current; current = current.parentNode) if (current === this) return true;
    return false;
  }
  closest(selector) {
    for (let current = this; current; current = current.parentNode) {
      if (current.matches && current.matches(selector)) return current;
    }
    return null;
  }
  matches(selector) {
    if (this.nodeType !== 1) return false;
    return selector.split(',').map((part) => part.trim()).some((part) => {
      if (part === 'button:not([disabled])') return this.tagName === 'BUTTON' && !this.disabled;
      if (part === 'input:not([disabled])') return this.tagName === 'INPUT' && !this.disabled;
      if (part === '[tabindex]:not([tabindex="-1"])') {
        return this.hasAttribute('tabindex') && this.getAttribute('tabindex') !== '-1';
      }
      if (part === '.td-shell-search:not(.td-is-open)') {
        return this.classList.contains('td-shell-search') && !this.classList.contains('td-is-open');
      }
      if (part === '[hidden]') return Boolean(this.hidden) || this.hasAttribute('hidden');
      if (part === '[inert]') return Boolean(this.inert) || this.hasAttribute('inert');
      if (part.startsWith('.')) return this.classList.contains(part.slice(1));
      const attribute = /^\[([\w-]+)(?:="([^"]*)")?\]$/.exec(part);
      if (attribute) {
        return attribute[2] === undefined
          ? this.hasAttribute(attribute[1])
          : this.getAttribute(attribute[1]) === attribute[2];
      }
      return this.tagName === part.toUpperCase();
    });
  }
  querySelectorAll(selector) {
    const found = [];
    const visit = (node) => {
      node.children.forEach((child) => {
        if (child.matches(selector)) found.push(child);
        visit(child);
      });
    };
    visit(this);
    return found;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}

function harness({ stored = {}, path: page = '/docs/current/', scope = '/', withRegistry = true } = {}) {
  const storage = new Map(Object.entries(stored));
  const opened = [];
  const assigned = [];
  const frames = [];
  const doc = {
    activeElement: null,
    listeners: new Map(),
    title: 'Current page | Site',
    createElement(tag) { const node = new Node(tag); node.ownerDocument = doc; return node; },
    createTextNode(text) { const node = new Node('#text'); node.text = String(text); node.ownerDocument = doc; return node; },
    createDocumentFragment() { const node = new Node('#fragment'); node.ownerDocument = doc; return node; },
    addEventListener(type, fn) { this.listeners.set(type, (this.listeners.get(type) || []).concat(fn)); },
    getElementById(id) { return this.body.querySelector(`[id="${id}"]`); },
    querySelector(selector) {
      if (selector === 'meta[property="og:title"]') return this.meta;
      return this.body.querySelector(selector);
    },
    contains(node) { return this.body.contains(node); },
  };
  const html = doc.createElement('html');
  html.setAttribute('lang', 'en');
  doc.documentElement = html;
  doc.body = doc.createElement('body');
  html.appendChild(doc.body);
  doc.meta = doc.createElement('meta');
  doc.meta.setAttribute('content', 'Current page');

  const root = doc.createElement('div');
  root.id = 'td-shell-history';
  root.hidden = true;
  root.setAttribute('data-td-history-scope', scope);
  root.setAttribute('data-td-t-empty', 'Nothing yet');
  root.setAttribute('data-td-t-results', '{count} results');
  root.setAttribute('data-td-t-cleared', 'Cleared');
  root.setAttribute('data-td-t-removed', 'Removed');
  const backdrop = doc.createElement('div');
  backdrop.setAttribute('data-td-history-close', '');
  root.appendChild(backdrop);
  const panel = doc.createElement('div');
  panel.className = 'td-shell-search__panel';
  const input = doc.createElement('input');
  input.className = 'td-shell-search__input';
  panel.appendChild(input);
  const list = doc.createElement('div');
  list.className = 'td-shell-search__list';
  panel.appendChild(list);
  const empty = doc.createElement('div');
  empty.setAttribute('data-td-history-empty', '');
  panel.appendChild(empty);
  const status = doc.createElement('div');
  status.setAttribute('data-td-history-status', '');
  panel.appendChild(status);
  const clear = doc.createElement('button');
  clear.setAttribute('data-td-history-clear', '');
  panel.appendChild(clear);
  root.appendChild(panel);
  doc.body.appendChild(root);
  const opener = doc.createElement('button');
  doc.body.appendChild(opener);

  const surfaces = new Map();
  const closedOthers = [];
  const executors = new Map();
  const win = {
    location: {
      href: 'https://example.test' + page,
      origin: 'https://example.test',
      pathname: page.split('?')[0],
      search: page.includes('?') ? page.slice(page.indexOf('?')) : '',
      assign(url) { assigned.push(url); },
    },
    localStorage: {
      getItem(key) { return storage.has(key) ? storage.get(key) : null; },
      setItem(key, value) { storage.set(key, String(value)); },
      removeItem(key) { storage.delete(key); },
    },
    open(url, target, features) { opened.push([url, target, features]); },
    requestAnimationFrame(fn) { frames.push(fn); },
    setTimeout(fn) { fn(); return 1; },
    clearTimeout() {},
    matchMedia() { return { matches: true }; },
    addEventListener() {},
  };
  const coordinator = {
    register(name, close) { surfaces.set(name, close); },
    closeOthers(name) { closedOthers.push(name); },
  };
  const registry = withRegistry ? {
    get(id) { return id === 'browse_history' ? { id, available: true } : null; },
    registerExecutor(id, fn) { executors.set(id, fn); },
  } : null;
  const instance = history.init({
    document: doc, window: win, coordinator, registry, now: () => 1_000_000_000,
  });
  const key = history.keyOf(scope);
  return {
    doc, win, html, root, input, list, empty, status, clear, opener, storage, opened, assigned,
    frames, surfaces, closedOthers, executors, instance, key,
    entries: () => JSON.parse(storage.get(key) || '[]'),
    rows: () => list.querySelectorAll('[role="option"]'),
    keydown(values) { return input.dispatch('keydown', values); },
    docKey(values) {
      const event = { key: '', shiftKey: false, preventDefault() { this.defaultPrevented = true; }, ...values };
      (doc.listeners.get('keydown') || []).forEach((fn) => fn(event));
      return event;
    },
  };
}

const MINUTE = 60 * 1000;

// ----------------------------------------------------------- recording
{
  const h = harness();
  assert.deepEqual(h.entries(), [{ url: '/docs/current/', title: 'Current page', time: 1_000_000_000 }],
    'the visit is recorded under the site key with its og:title');
  assert.equal(h.key, 'td-history:/');
}
{
  const previous = [
    { url: '/docs/a/', title: 'A', time: 1_000_000_000 - 5 * MINUTE },
    { url: '/docs/current/', title: 'Old title', time: 1 },
    { url: '//evil.example/', title: 'Evil', time: 2 },
    { url: '/\\evil.example/', title: 'Evil', time: 3 },
    { url: '/docs/b/', title: 'B', time: 'soon' },
    'junk',
  ];
  const h = harness({ stored: { 'td-history:/': JSON.stringify(previous) }, path: '/docs/current/?tab=2' });
  assert.deepEqual(h.entries().map((entry) => entry.url), ['/docs/current/?tab=2', '/docs/a/', '/docs/current/'],
    'the visit moves to the top; tampered entries are dropped rather than repaired');
}
{
  const many = Array.from({ length: 130 }, (_, n) => ({ url: `/p/${n}/`, title: `P${n}`, time: n + 1 }));
  const h = harness({ stored: { 'td-history:/': JSON.stringify(many) } });
  assert.equal(h.entries().length, history.LIMIT, 'the list keeps the newest hundred pages');
}
{
  const other = JSON.stringify([{ url: '/b/page/', title: 'Site B', time: 5 }]);
  const h = harness({ scope: '/a/', path: '/a/docs/', stored: { 'td-history:/a/': other, 'td-history:/b/': other } });
  assert.equal(h.key, 'td-history:/a/');
  assert.deepEqual(h.entries().map((entry) => entry.url), ['/a/docs/'],
    'another site on the same origin never enters this history');
  assert.equal(h.storage.get('td-history:/b/'), other, 'the other site keeps its own list');
}
{
  const h = harness({ withRegistry: false });
  h.doc.body.classList.add('td-404');
  h.storage.clear();
  assert.equal(history.record(h.doc, h.win, () => 5), false, 'a missing page is not history');
  assert.equal(h.storage.size, 0);
}

// -------------------------------------------------------------- overlay
{
  const stored = [
    { url: '/docs/current/', title: 'Current page', time: 1 },
    { url: '/docs/install/', title: 'Install the server', time: 1_000_000_000 - 2 * MINUTE },
    { url: '/docs/%E9%85%8D%E7%BD%AE/', title: '配置参考', time: 1_000_000_000 - 90 * MINUTE },
    { url: '/blog/release/', title: 'Release notes', time: 1_000_000_000 - 3 * 24 * 60 * MINUTE },
  ];
  const h = harness({ stored: { 'td-history:/': JSON.stringify(stored) } });
  h.opener.focus();
  assert.equal(typeof h.surfaces.get('history'), 'function', 'the overlay registers with the surface coordinator');
  assert.equal(typeof h.executors.get('browse_history'), 'function', 'the palette row gets its executor');

  h.instance.open();
  assert.deepEqual(h.closedOthers, ['history'], 'opening closes the palette and other surfaces first');
  assert.equal(h.root.hidden, false);
  assert.equal(h.html.hasAttribute('data-td-shell-lock'), true, 'the overlay takes the shared shortcut lock');
  assert.equal(h.doc.activeElement, h.input, 'the filter takes focus');
  h.frames.splice(0).forEach((fn) => fn());
  assert.equal(h.root.classList.contains('td-is-open'), true);
  const titles = h.rows().map((row) => row.querySelector('.td-shell-search__item-title').textContent);
  assert.deepEqual(titles, ['Install the server', '配置参考', 'Release notes'],
    'the page being read is left out, newest first');
  const refs = h.rows().map((row) => row.querySelector('.td-shell-search__item-ref').textContent);
  assert.match(refs[0], /^\/docs\/install\/ · 2 minutes ago$/);
  assert.match(refs[1], /^\/docs\/配置\/ · /, 'paths are shown decoded');
  assert.equal(h.rows()[0].getAttribute('aria-selected'), 'true', 'H then Enter returns to the last page');
  assert.equal(h.input.getAttribute('aria-activedescendant'), h.rows()[0].id);

  h.input.value = 'RELEASE';
  h.input.dispatch('input');
  assert.deepEqual(h.rows().map((row) => row.querySelector('.td-shell-search__item-title').textContent),
    ['Release notes'], 'typing filters by title and path, ignoring case');
  assert.equal(h.rows()[0].querySelector('mark').textContent, 'Release', 'the match is marked');
  h.input.value = 'nothing like it';
  h.input.dispatch('input');
  assert.equal(h.rows().length, 0);
  assert.equal(h.list.children.length, 0, 'the listbox holds options only');
  assert.equal(h.empty.hidden, false);
  assert.equal(h.empty.textContent, 'No results');
  h.input.value = '';
  h.input.dispatch('input');
  assert.equal(h.empty.hidden, true, 'the empty state hides again once rows return');

  h.keydown({ key: 'ArrowDown' });
  assert.equal(h.rows()[1].getAttribute('aria-selected'), 'true', 'ArrowDown moves the selection');
  const opened = h.keydown({ key: 'Enter', ctrlKey: true });
  assert.equal(opened.defaultPrevented, true);
  assert.deepEqual(h.opened, [['https://example.test/docs/%E9%85%8D%E7%BD%AE/', '_blank', 'noopener']],
    'Ctrl+Enter opens the page in a new tab and keeps the overlay');
  assert.equal(h.instance.isOpen(), true);

  h.keydown({ key: 'Delete', shiftKey: true });
  assert.deepEqual(h.entries().map((entry) => entry.url), ['/docs/current/', '/docs/install/', '/blog/release/'],
    'Shift+Delete forgets the selected page');
  assert.equal(h.rows()[1].getAttribute('aria-selected'), 'true', 'the selection stays in place');
  assert.equal(h.rows().length, 2);

  h.keydown({ key: 'Enter' });
  assert.deepEqual(h.assigned, ['https://example.test/blog/release/'], 'Enter opens the selected page');
  assert.equal(h.instance.isOpen(), false, 'opening a page closes the overlay');
  assert.equal(h.html.hasAttribute('data-td-shell-lock'), false);

  h.opener.focus();
  h.instance.open();
  assert.equal(h.clear.disabled, false);
  h.clear.click();
  assert.equal(h.storage.has('td-history:/'), false, 'Clear history removes the stored list');
  assert.equal(h.list.children.length, 0);
  assert.equal(h.empty.textContent, 'Nothing yet');
  assert.equal(h.clear.disabled, true, 'nothing left to clear');
  const escape = h.docKey({ key: 'Escape' });
  assert.equal(escape.defaultPrevented, true);
  assert.equal(h.instance.isOpen(), false, 'Escape closes the overlay');
  assert.equal(h.root.hidden, true);
  assert.equal(h.doc.activeElement, h.opener, 'focus returns to where the reader was');

  h.executors.get('browse_history')();
  assert.equal(h.instance.isOpen(), true, 'the Command Palette row opens the same overlay');
  h.surfaces.get('history')(false);
  assert.equal(h.instance.isOpen(), false, 'a coordinated close is honored');
}

{
  // Traversal segments cannot escape a subpath scope; legitimate dots inside
  // a segment and root queries still pass.
  assert.equal(history.sanitize({ url: '/a/../b/secret/', title: 'Escape', time: 5 }, '/a/'), null);
  assert.equal(history.sanitize({ url: '/a/%2e%2e/b/secret/', title: 'Encoded escape', time: 5 }, '/a/'), null);
  assert.equal(history.sanitize({ url: '/a/.%2E/b/', title: 'Mixed escape', time: 5 }, '/a/'), null);
  assert.equal(history.sanitize({ url: '/a/v1..v2/', title: 'Release range', time: 5 }, '/a/')?.url, '/a/v1..v2/');
  assert.equal(history.sanitize({ url: '/a?tab=1', title: 'Root query', time: 5 }, '/a/')?.url, '/a?tab=1');
}
{
  // First visit: only the current page is stored, so the displayed list is
  // empty and Clear history starts disabled.
  const h = harness();
  h.instance.open();
  assert.equal(h.rows().length, 0);
  assert.equal(h.empty.textContent, 'Nothing yet');
  assert.equal(h.clear.disabled, true, 'Clear history is disabled when no earlier page is listed');

  // IME composition suppresses filtering and Escape does not close the overlay.
  h.input.dispatch('compositionstart');
  const composingEsc = h.docKey({ key: 'Escape', isComposing: true, keyCode: 229 });
  assert.notEqual(composingEsc.defaultPrevented, true, 'Escape during IME composition is not swallowed');
  assert.equal(h.instance.isOpen(), true, 'IME Escape keeps the history overlay open');
  h.input.dispatch('compositionend');
  const finalEsc = h.docKey({ key: 'Escape' });
  assert.equal(finalEsc.defaultPrevented, true);
  assert.equal(h.instance.isOpen(), false, 'Escape after compositionend closes the overlay');
}
{
  // Focus restoration skips a closing Command Palette input and falls back to
  // #td-main-content if the original opener becomes hidden before close.
  const h = harness();
  const main = h.doc.createElement('main');
  main.id = 'td-main-content';
  h.doc.body.appendChild(main);
  const closingPalette = h.doc.createElement('div');
  closingPalette.className = 'td-shell-search';
  const paletteInput = h.doc.createElement('input');
  closingPalette.appendChild(paletteInput);
  h.doc.body.appendChild(closingPalette);
  paletteInput.focus();
  h.instance.open();
  h.instance.close(true);
  assert.notEqual(h.doc.activeElement, paletteInput, 'closing history never restores focus into a closing search overlay');

  h.opener.focus();
  h.instance.open();
  h.opener.hidden = true;
  h.instance.close(true);
  assert.equal(h.doc.activeElement, main, 'when the opener hides, focus falls back to #td-main-content');
}
{
  // Without a list root the runtime still records visits and offers nothing to open.
  const h = harness();
  h.root.parentNode.children = [];
  const bare = history.init({ document: h.doc, window: h.win, now: () => 7 });
  assert.equal(bare.open(), false);
  assert.equal(bare.isOpen(), false);
}

console.log('browsing history checks passed');
