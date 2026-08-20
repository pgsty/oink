'use strict';

// Headless contract tests for the blog index form switch in
// assets/js/docs-shell.js: what the button does to the root element, what it
// remembers, and the two states it has to read the first click from -- a
// stored choice, or the form the site published. A DOM shim covers exactly the
// calls this init makes; every other init in the file bails on its own missing
// selector.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const SOURCE = fs.readFileSync(
  path.join(__dirname, '..', '..', 'assets/js/docs-shell.js'),
  'utf8',
);

function element(attributes) {
  const attrs = new Map(Object.entries(attributes || {}));
  return {
    hidden: true,
    handlers: {},
    classList: { add() {}, remove() {}, contains: () => false, toggle() {} },
    style: { setProperty() {}, removeProperty() {} },
    getAttribute: (name) => (attrs.has(name) ? attrs.get(name) : null),
    setAttribute: (name, value) => attrs.set(name, String(value)),
    removeAttribute: (name) => attrs.delete(name),
    hasAttribute: (name) => attrs.has(name),
    addEventListener(type, handler) {
      this.handlers[type] = handler;
    },
    removeEventListener() {},
    querySelector: () => null,
    querySelectorAll: () => [],
    getBoundingClientRect: () => ({ top: 0, bottom: 0, left: 0, right: 0, width: 0, height: 0 }),
    closest: () => null,
    contains: () => false,
    appendChild() {},
    focus() {},
  };
}

// One page: the switch, the wrapper that records the published form, and a
// root element that starts with whatever prepaint restored.
function bootstrap({ stored, published, refuseWrites }) {
  const toggle = element({});
  const posts = element({ 'data-td-blog-default': published });
  const root = element(stored ? { 'data-td-blog-index': stored } : {});
  const store = new Map(stored ? [['td-blog-index', stored]] : []);

  const document = {
    documentElement: root,
    body: element({}),
    addEventListener() {},
    removeEventListener() {},
    querySelectorAll: () => [],
    getElementById: () => null,
    createElement: () => element({}),
    querySelector(selector) {
      if (selector === '[data-td-blog-index-toggle]') return toggle;
      if (selector === '.td-blog-posts[data-td-blog-default]') return posts;
      return null;
    },
  };

  const context = {
    document,
    localStorage: {
      getItem: (key) => (store.has(key) ? store.get(key) : null),
      setItem: (key, value) => {
        if (refuseWrites) throw new Error('QuotaExceededError');
        store.set(key, String(value));
      },
      removeItem: (key) => store.delete(key),
    },
    matchMedia: () => ({ matches: false, addEventListener() {}, removeEventListener() {} }),
    addEventListener() {},
    removeEventListener() {},
    requestAnimationFrame: (fn) => fn(),
    getComputedStyle: () => ({ getPropertyValue: () => '' }),
    setTimeout,
    clearTimeout,
    console,
  };
  context.window = context;
  context.self = context;
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(SOURCE, context);

  return { toggle, posts, root, store };
}

test('the switch is hidden until the runtime claims it', () => {
  const { toggle } = bootstrap({ published: 'list' });
  assert.equal(toggle.hidden, false, 'a page with JavaScript reveals the control');
});

test('the published form is on the root element before the reader touches it', () => {
  // Prepaint only writes the attribute when a choice is stored. Settling it
  // here is what keeps the glyph from offering the form the page is in.
  const { root } = bootstrap({ published: 'cards' });
  assert.equal(root.getAttribute('data-td-blog-index'), 'cards');
});

test('a stored choice survives the settling', () => {
  const { root } = bootstrap({ stored: 'list', published: 'cards' });
  assert.equal(root.getAttribute('data-td-blog-index'), 'list');
});

test('a form outside the cycle settles on the list', () => {
  // A stale stored value -- an old experiment, a renamed form -- must not
  // leave the page showing nothing.
  const { root } = bootstrap({ stored: 'grid', published: 'cards' });
  assert.equal(root.getAttribute('data-td-blog-index'), 'list');
});

test('a page with no index leaves the control alone', () => {
  // The same file runs on an article. Nothing to switch, nothing revealed.
  const toggle = element({});
  const document = {
    documentElement: element({}),
    body: element({}),
    addEventListener() {},
    querySelectorAll: () => [],
    getElementById: () => null,
    createElement: () => element({}),
    querySelector: (selector) =>
      (selector === '[data-td-blog-index-toggle]' ? toggle : null),
  };
  const context = {
    document,
    localStorage: { getItem: () => null, setItem() {}, removeItem() {} },
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    addEventListener() {},
    requestAnimationFrame: (fn) => fn(),
    getComputedStyle: () => ({ getPropertyValue: () => '' }),
    setTimeout,
    clearTimeout,
    console,
  };
  context.window = context;
  context.self = context;
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(SOURCE, context);
  assert.equal(toggle.hidden, true, 'no wrapper means no control');
});

test('the first click reads the published form when nothing is stored', () => {
  const { toggle, root, store } = bootstrap({ published: 'list' });
  toggle.handlers.click();
  assert.equal(root.getAttribute('data-td-blog-index'), 'cards');
  assert.equal(store.get('td-blog-index'), 'cards');
});

test('the first click reads a stored choice ahead of the published form', () => {
  // Published as rows, but this reader already chose cards elsewhere: the
  // click has to advance from cards, not restart from the published form.
  const { toggle, root } = bootstrap({ stored: 'cards', published: 'list' });
  toggle.handlers.click();
  assert.equal(root.getAttribute('data-td-blog-index'), 'table');
});

test('three clicks walk list, cards, table and return', () => {
  const { toggle, root, store } = bootstrap({ published: 'cards' });
  toggle.handlers.click();
  assert.equal(root.getAttribute('data-td-blog-index'), 'table');
  toggle.handlers.click();
  assert.equal(root.getAttribute('data-td-blog-index'), 'list');
  toggle.handlers.click();
  assert.equal(root.getAttribute('data-td-blog-index'), 'cards');
  assert.equal(store.get('td-blog-index'), 'cards');
});

test('a refused write does not break the switch', () => {
  // Private browsing throws on setItem. The choice is lost on the next page,
  // but this one still changes form rather than dying on the click.
  const { toggle, root, store } = bootstrap({ published: 'list', refuseWrites: true });
  assert.doesNotThrow(() => toggle.handlers.click());
  assert.equal(root.getAttribute('data-td-blog-index'), 'cards');
  assert.equal(store.has('td-blog-index'), false, 'nothing was persisted');
});
