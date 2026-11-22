'use strict';

const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');

test('footer-collapse toggles fat-footer visibility, updates labels, and persists in storage', () => {
  global.__OINK_FOOTER_COLLAPSE_MANUAL_INIT__ = true;
  const footerPath = path.join(__dirname, '..', '..', 'assets/js/footer-collapse.js');
  delete require.cache[require.resolve(footerPath)];
  const footerCollapse = require(footerPath);

  const store = new Map([['td-footer-collapsed', '1']]);
  const storage = {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
  };

  const attrs = new Map();
  const classes = new Set();
  const listeners = new Map();
  const toggle = {
    dataset: { tdLabelCollapse: 'Collapse footer', tdLabelExpand: 'Expand footer' },
    classList: {
      toggle(name, force) {
        if (force) classes.add(name);
        else classes.delete(name);
      },
      contains: (name) => classes.has(name),
    },
    setAttribute: (k, v) => attrs.set(k, String(v)),
    getAttribute: (k) => attrs.get(k) || null,
    addEventListener: (name, fn) => listeners.set(name, fn),
  };
  const target = { hidden: false };
  const doc = {
    querySelector: (sel) => (sel === '[data-td-footer-toggle]' ? toggle : null),
    getElementById: (id) => (id === 'td-site-footer' ? target : null),
  };

  const instance = footerCollapse.init({ document: doc, storage });
  assert.ok(instance);
  // Restored collapsed state from storage without rewriting storage
  assert.equal(target.hidden, true);
  assert.equal(toggle.getAttribute('aria-expanded'), 'false');
  assert.equal(toggle.getAttribute('aria-label'), 'Expand footer');
  assert.equal(toggle.classList.contains('td-is-collapsed'), true);

  // Click expands and clears storage key
  listeners.get('click')();
  assert.equal(target.hidden, false);
  assert.equal(toggle.getAttribute('aria-expanded'), 'true');
  assert.equal(toggle.getAttribute('aria-label'), 'Collapse footer');
  assert.equal(store.has('td-footer-collapsed'), false);

  // Second click collapses and persists '1'
  listeners.get('click')();
  assert.equal(target.hidden, true);
  assert.equal(store.get('td-footer-collapsed'), '1');
});
