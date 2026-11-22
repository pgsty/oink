'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

test('appearance registers switch_preset once across DOMContentLoaded and falls back to manifest options when chrome is suppressed', () => {
  const attributes = new Map([
    ['data-td-site-preset', 'paper'],
    ['data-td-preset', 'paper'],
  ]);
  const storage = new Map();
  const docListeners = new Map();
  let registered = 0;
  let executor = null;

  const fakeDocument = {
    readyState: 'loading',
    documentElement: {
      getAttribute(name) { return attributes.get(name) || null; },
      setAttribute(name, value) { attributes.set(name, String(value)); },
      removeAttribute(name) { attributes.delete(name); },
      hasAttribute(name) { return attributes.has(name); },
      toggleAttribute(name, force) {
        if (force) attributes.set(name, '');
        else attributes.delete(name);
      },
    },
    addEventListener(name, cb) { docListeners.set(name, cb); },
    querySelectorAll() { return []; },
    getElementById() { return null; },
  };

  const fakeWindow = {
    scrollY: 0,
    localStorage: {
      getItem(k) { return storage.get(k) || null; },
      setItem(k, v) { storage.set(k, String(v)); },
      removeItem(k) { storage.delete(k); },
    },
    addEventListener() {},
    requestAnimationFrame(cb) { cb(); },
    dispatchEvent() {},
    OinkActions: {
      get(id) {
        return id === 'switch_preset'
          ? { id, options: [{ value: 'paper' }, { value: 'slate' }, { value: 'ink' }] }
          : null;
      },
      registerExecutor(id, fn) {
        assert.equal(id, 'switch_preset');
        registered += 1;
        if (registered > 1) throw new Error('duplicate switch_preset registration');
        executor = fn;
      },
    },
  };

  const source = fs.readFileSync(
    path.join(__dirname, '..', '..', 'assets/js/appearance.js'),
    'utf8',
  );
  vm.runInNewContext(source, {
    window: fakeWindow,
    document: fakeDocument,
    CustomEvent: function CustomEvent(type, init) {
      this.type = type;
      this.detail = init && init.detail;
    },
    Promise,
    Error,
  });

  assert.equal(registered, 1);
  assert.equal(typeof docListeners.get('DOMContentLoaded'), 'function');
  docListeners.get('DOMContentLoaded')();
  assert.equal(registered, 1);

  assert.deepEqual(Array.from(fakeWindow.OinkAppearance.offered()), ['paper', 'slate', 'ink']);
  const result = executor({ value: 'ink' });
  assert.deepEqual({ preset: result.preset }, { preset: 'ink' });
  assert.equal(attributes.get('data-td-preset'), 'ink');
  assert.equal(storage.get('td-preset'), 'ink');
});
