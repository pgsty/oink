'use strict';

// Headless contract tests for assets/js/tabs.js: activation, roving tabindex,
// keyboard order (LTR / RTL), grouped sync + persistence + hash, ungrouped
// sets, and peers that lack a value. A tiny DOM shim covers exactly the
// selectors the runtime uses.

const assert = require('node:assert/strict');
const path = require('node:path');
const test = require('node:test');

const tabs = require(path.join(__dirname, '..', '..', 'assets/js/tabs.js'));

function element(tag, attrs = {}) {
  const attributes = new Map(Object.entries(attrs));
  const listeners = new Map();
  const el = {
    tagName: tag.toUpperCase(),
    nodeType: 1,
    children: [],
    parentNode: null,
    hidden: false,
    focused: false,
    textContent: attrs.text || '',
    className: attrs.class || '',
    get classList() {
      const self = this;
      return {
        contains: (c) => self.className.split(/\s+/).includes(c),
        add: (c) => { if (!self.className.split(/\s+/).includes(c)) self.className = (self.className + ' ' + c).trim(); },
      };
    },
    getAttribute(name) { return attributes.has(name) ? attributes.get(name) : null; },
    setAttribute(name, value) { attributes.set(name, String(value)); if (name === 'class') this.className = String(value); },
    removeAttribute(name) { attributes.delete(name); },
    hasAttribute(name) { return attributes.has(name); },
    addEventListener(name, cb) { listeners.set(name, cb); },
    dispatch(name, event) { const cb = listeners.get(name); return cb ? cb(event) : undefined; },
    focus() { this.focused = true; },
    append(...nodes) { nodes.forEach((n) => { n.parentNode = this; this.children.push(n); }); return this; },
    matches(selector) { return matches(this, selector); },
    closest(selector) { let n = this; while (n) { if (n.matches && n.matches(selector)) return n; n = n.parentNode; } return null; },
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; },
    querySelectorAll(selector) {
      // Only ':scope > a > b' style child selectors are needed.
      const parts = selector.replace(/^:scope\s*>\s*/, '').split(/\s*>\s*/);
      let current = [this];
      for (const part of parts) {
        const next = [];
        current.forEach((node) => node.children.forEach((child) => { if (matches(child, part)) next.push(child); }));
        current = next;
      }
      return current;
    },
  };
  if (attrs.class) attributes.set('class', attrs.class);
  return el;
}

function matches(el, selector) {
  // Supports: .class, [attr], [attr="v"], tag, combinations without spaces.
  const tokens = selector.match(/\.[\w-]+|\[[^\]]+\]|[a-z]+/g) || [];
  return tokens.every((token) => {
    if (token.startsWith('.')) return el.className.split(/\s+/).includes(token.slice(1));
    if (token.startsWith('[')) {
      const m = token.match(/^\[([\w-]+)(?:="([^"]*)")?\]$/);
      if (!m) return false;
      if (m[2] === undefined) return el.hasAttribute(m[1]);
      return el.getAttribute(m[1]) === m[2];
    }
    return el.tagName === token.toUpperCase();
  });
}

function tabset({ group, values, defaultValue, id = 'set' }) {
  const root = element('div', { class: 'td-tabs', 'data-td-tabs': '' });
  if (group) root.setAttribute('data-td-tabs-group', group);
  root.setAttribute('data-td-tabs-default', defaultValue || values[0]);
  const list = element('div', { class: 'td-tabs__list', role: 'tablist' });
  root.append(list);
  values.forEach((value, i) => {
    const panelID = group ? `${group}-${value}` : `${id}-${value}`;
    list.append(element('button', { class: 'td-tabs__tab', role: 'tab', id: `${panelID}-tab`, 'aria-selected': i === 0 ? 'true' : 'false', tabindex: i === 0 ? '0' : '-1', 'data-td-tabs-value': value, text: value }));
    root.append(element('section', { class: 'td-tabs__panel', role: 'tabpanel', id: panelID, 'data-td-tabs-value': value }));
  });
  return root;
}

function memoryStorage() {
  const values = new Map();
  return { getItem: (k) => (values.has(k) ? values.get(k) : null), setItem: (k, v) => values.set(k, String(v)), values };
}

function env(sets, { hash = '', dir = 'ltr' } = {}) {
  const byId = new Map();
  const walk = (n) => { if (n.getAttribute && n.getAttribute('id')) byId.set(n.getAttribute('id'), n); n.children.forEach(walk); };
  sets.forEach(walk);
  const doc = { documentElement: { dir }, getElementById: (id) => byId.get(id) || null };
  const history = { state: null, replaced: [], replaceState(state, _t, url) { this.replaced.push(url); } };
  const win = { location: { pathname: '/p/', search: '', hash }, history, matchMedia: () => ({ matches: true }) };
  return { doc, win, history };
}

test('activation hides other panels and moves the roving tabindex', () => {
  const root = tabset({ values: ['a', 'b', 'c'] });
  assert.equal(tabs.activate(root, 'b'), true);
  const [ta, tb] = root.querySelectorAll(':scope > .td-tabs__list > [role="tab"]');
  assert.equal(ta.getAttribute('aria-selected'), 'false');
  assert.equal(ta.getAttribute('tabindex'), '-1');
  assert.equal(tb.getAttribute('aria-selected'), 'true');
  assert.equal(tb.getAttribute('tabindex'), '0');
  const panels = root.querySelectorAll(':scope > .td-tabs__panel');
  assert.deepEqual(panels.map((p) => p.hidden), [true, false, true]);
  assert.equal(tabs.activate(root, 'missing'), false, 'unknown value leaves the set unchanged');
  assert.equal(tb.getAttribute('aria-selected'), 'true');
});

test('grouped sets sync, persist and update the hash; ungrouped sets do not', () => {
  const storage = memoryStorage();
  const one = tabset({ group: 'pm', values: ['npm', 'pnpm', 'yarn'] });
  const two = tabset({ group: 'pm', values: ['npm', 'pnpm'] });
  const local = tabset({ values: ['x', 'y'], id: 'local' });
  const { doc, win, history } = env([one, two, local]);
  const controller = tabs.createController(doc, win, { storage });
  [one, two, local].forEach(controller.enhance);
  assert.ok(one.hasAttribute('data-td-tabs-ready'));

  controller.select(one, 'pnpm', 'click');
  assert.equal(two.querySelector(':scope > .td-tabs__list > [aria-selected="true"]').getAttribute('data-td-tabs-value'), 'pnpm', 'peer synced');
  assert.equal(storage.getItem('td-tabs:v1:pm'), 'pnpm');
  assert.deepEqual(history.replaced, ['/p/#pm-pnpm']);

  controller.select(one, 'yarn', 'click');
  assert.equal(two.querySelector(':scope > .td-tabs__list > [aria-selected="true"]').getAttribute('data-td-tabs-value'), 'pnpm', 'peer without the value keeps its selection');

  controller.select(local, 'y', 'click');
  assert.equal(storage.getItem('td-tabs:v1:'), null);
  assert.equal(history.replaced.length, 2, 'ungrouped sets do not touch the hash');
});

test('stored value wins over default; hash wins over stored', () => {
  const storage = memoryStorage();
  storage.setItem('td-tabs:v1:pm', 'pnpm');
  const one = tabset({ group: 'pm', values: ['npm', 'pnpm', 'yarn'] });
  const { doc, win } = env([one], { hash: '#pm-yarn' });
  const controller = tabs.createController(doc, win, { storage });
  controller.enhance(one);
  assert.equal(one.querySelector(':scope > .td-tabs__list > [aria-selected="true"]').getAttribute('data-td-tabs-value'), 'pnpm');
  assert.equal(controller.applyHash(), true);
  assert.equal(one.querySelector(':scope > .td-tabs__list > [aria-selected="true"]').getAttribute('data-td-tabs-value'), 'yarn');
});

test('keyboard: arrows wrap and respect RTL, Home/End jump, focus follows', () => {
  for (const dir of ['ltr', 'rtl']) {
    const root = tabset({ values: ['a', 'b', 'c'] });
    const { doc, win } = env([root], { dir });
    const controller = tabs.createController(doc, win, { storage: memoryStorage() });
    controller.enhance(root);
    const list = root.querySelector(':scope > .td-tabs__list');
    const [ta, tb, tc] = list.children;
    const forward = dir === 'rtl' ? 'ArrowLeft' : 'ArrowRight';
    const backward = dir === 'rtl' ? 'ArrowRight' : 'ArrowLeft';
    let prevented = 0;
    const press = (target, key) => list.dispatch('keydown', { key, target, preventDefault: () => { prevented += 1; } });
    press(ta, forward);
    assert.equal(tb.getAttribute('aria-selected'), 'true', dir);
    assert.equal(tb.focused, true, dir);
    press(tb, backward);
    assert.equal(ta.getAttribute('aria-selected'), 'true', dir);
    press(ta, backward);
    assert.equal(tc.getAttribute('aria-selected'), 'true', `${dir} wraps backwards`);
    press(tc, 'Home');
    assert.equal(ta.getAttribute('aria-selected'), 'true', dir);
    press(ta, 'End');
    assert.equal(tc.getAttribute('aria-selected'), 'true', dir);
    assert.equal(prevented, 5, dir);
  }
});
